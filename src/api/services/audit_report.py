"""SkillSpector 风险评估报告的读取侧聚合。

详情页「查看风险评估报告」页面需要的结构化数据（综合得分与等级、四类风险分类聚合、
17 维度聚合、逐条风险明细、中文摘要）在库中并不预聚合，这里基于
``security_audits.details`` 中保存的 SkillSpector ``report.json`` 在读取时派生。

数据来源（按优先级）：
- ``details.skillspector_report.risk_assessment``：score / severity / recommendation
- ``details.skillspector_report.issues[]``：逐条风险（category / severity / remediation /
  location / code_snippet / explanation）
- ``details.skillspector_score`` / ``details.skillspector_version``：分数与引擎版本
- ``skill.risk_score``：兜底分数

分类体系与中文本地化见 :mod:`src.api.services.skillspector_rules`（规则目录来自
``RISK_MODEL_SUMMARY.md``）：四大类 -> 17 个风险维度 -> 检测项（规则 ID）。
风险描述与修复建议统一输出中文，SkillSpector 原始英文文案不再直接透出。
"""

from __future__ import annotations

from typing import Any

from src.api.services.skillspector_rules import (
    CATEGORIES,
    DIMENSION_BY_KEY,
    DIMENSIONS,
    RULE_CATALOG,
    resolve_dimension,
    rule_meta,
)

__all__ = [
    "MAX_FINDINGS",
    "resolve_dimension",
    "severity_group",
    "build_audit_report",
]

# 单次返回的风险明细上限（防止超大报告撑爆响应体）
MAX_FINDINGS = 500

# 规则目录规模（“检测项”总数，与设计稿同口径的静态值）
RULE_COUNT = len(RULE_CATALOG)

# 分数分档 -> (等级 key, 中文标签, 描述)。与设计稿“等级划分”一致：0-20 安全 / 21-50 低 / 51-80 中 / 81-100 高
_LEVEL_TIERS: tuple[tuple[int, str, str, str], ...] = (
    (20, "safe", "安全", "无显著风险，可以放心使用"),
    (50, "low", "低风险", "风险较低，可以正常使用"),
    (80, "medium", "中风险", "存在一定风险，建议谨慎使用"),
    (100, "high", "高风险", "存在较严重问题，不建议直接安装"),
)

_UNKNOWN_LEVEL = ("unknown", "未检测", "暂无风险评估数据")

# SkillSpector severity -> 展示分组（CRITICAL/HIGH 合并为高风险）
_SEVERITY_GROUPS = {
    "CRITICAL": "high",
    "HIGH": "high",
    "MEDIUM": "medium",
    "LOW": "low",
}

# 展示分组的严重度排序（高风险在前）
_GROUP_ORDER = {"high": 0, "medium": 1, "low": 2}

# 维度在 17 维度体系中的顺序（用于聚合与明细的稳定排序）
_DIMENSION_ORDER = {dimension.key: index for index, dimension in enumerate(DIMENSIONS)}


def severity_group(severity: str | None) -> str:
    """SkillSpector severity -> high/medium/low 展示分组（未知按 medium 处理）。"""
    return _SEVERITY_GROUPS.get(str(severity or "").strip().upper(), "medium")


def _dimension_group_key(dimension: str) -> str:
    """返回维度所属的分类 key。"""
    dimension_meta = DIMENSION_BY_KEY.get(dimension)
    return dimension_meta.category_key if dimension_meta else "privilege_code"


def _level_from_score(score: int | None) -> tuple[str, str, str]:
    if score is None:
        return _UNKNOWN_LEVEL
    for upper, key, label, description in _LEVEL_TIERS:
        if score <= upper:
            return key, label, description
    return _LEVEL_TIERS[-1][1], _LEVEL_TIERS[-1][2], _LEVEL_TIERS[-1][3]


def _resolve_score(details: dict[str, Any], report: dict[str, Any], skill: Any) -> int | None:
    """分数优先级：details.skillspector_score > report.risk_assessment.score > skills.risk_score。"""
    score = details.get("skillspector_score")
    if not isinstance(score, (int, float)):
        risk_assessment = report.get("risk_assessment") or {}
        score = risk_assessment.get("score")
    if not isinstance(score, (int, float)):
        score = getattr(skill, "risk_score", None)
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        return None
    return max(0, min(100, int(round(score))))


def _build_summary(
    score: int | None,
    level: str,
    level_label: str,
    stats: dict[str, int],
) -> str:
    """拼装“整体评估摘要”文案（数据驱动的中文摘要）。"""
    if score is None:
        return "暂无可用的安全评估数据，请等待审计完成后查看。"

    counts = []
    if stats["high"]:
        counts.append(f"{stats['high']} 项高风险")
    if stats["medium"]:
        counts.append(f"{stats['medium']} 项中风险")
    if stats["low"]:
        counts.append(f"{stats['low']} 项低风险")
    detected = "、".join(counts) if counts else "无风险项"

    suggestions = {
        "high": "建议优先修复高风险项后再使用。",
        "medium": "建议完成中风险项修复或评估影响后再使用。",
        "low": "建议关注低风险项并在后续版本中修复。",
        "safe": "整体安全状况良好，建议保持当前的权限与依赖管理实践。",
    }
    suggestion = suggestions.get(level, "建议结合实际使用场景评估风险。")
    return (
        f"该 Skill 综合得分 {score}/100，评估等级为{level_label}，"
        f"共检测到{detected}。{suggestion}"
    )


def _issue_sort_key(finding: dict[str, Any]) -> tuple[int, int, str, int]:
    """明细排序：严重度 -> 维度顺序 -> 文件 -> 起始行。"""
    location = finding.get("location") or {}
    return (
        _GROUP_ORDER.get(finding["severity_group"], 3),
        _DIMENSION_ORDER.get(finding["dimension_key"], len(_DIMENSION_ORDER)),
        str(location.get("file") or ""),
        int(location.get("start_line") or 0),
    )


def _build_finding(issue: dict[str, Any]) -> dict[str, Any]:
    """把一条 SkillSpector issue 归一化为中文本地化后的风险明细。"""
    dimension_key = resolve_dimension(issue)
    dimension = DIMENSION_BY_KEY[dimension_key]
    rule_id = str(issue.get("id") or "").strip().upper()
    rule = rule_meta(rule_id)

    severity = str(issue.get("severity") or "").strip().upper() or "LOW"
    location = issue.get("location") or {}
    # 中文本地化：优先用规则目录里的中文名称/建议，避免透出 SkillSpector 英文原文
    if rule:
        title = f"{rule.name}：{dimension.description}"
        remediation = rule.remediation
    else:
        title = f"{dimension.name}：{dimension.description}"
        remediation = None

    return {
        "id": rule_id,
        "rule_id": rule_id,
        "rule_name": rule.name if rule else None,
        "title": title,
        "dimension": dimension.name,
        "dimension_key": dimension_key,
        "category_key": dimension.category_key,
        "severity": severity,
        "severity_group": severity_group(severity),
        # 审计为一次性快照，暂不追踪修复状态；命中项默认待处理
        "status": "open",
        "remediation": remediation,
        "location": {
            "file": location.get("file"),
            "start_line": location.get("start_line"),
            "end_line": location.get("end_line"),
        }
        if location
        else None,
        "code_snippet": issue.get("code_snippet"),
        "truncated": bool(issue.get("truncated")),
    }


def _build_rule_rows(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """把同一维度下的命中项按检测项（规则 ID）聚合（“风险检测详情”的行）。"""
    ordered: dict[str, list[dict[str, Any]]] = {}
    for item in sorted(items, key=_issue_sort_key):
        key = item["rule_id"] or item["rule_name"] or item["dimension_key"]
        ordered.setdefault(key, []).append(item)

    rows: list[dict[str, Any]] = []
    for rule_items in ordered.values():
        rule_stats = {"high": 0, "medium": 0, "low": 0, "total": len(rule_items)}
        for item in rule_items:
            rule_stats[item["severity_group"]] += 1
        rows.append(
            {
                "rule_id": rule_items[0]["rule_id"],
                "rule_name": rule_items[0]["rule_name"],
                "stats": rule_stats,
                "max_severity_group": next(
                    group for group in ("high", "medium", "low") if rule_stats[group]
                ),
                "remediation": rule_items[0]["remediation"],
            }
        )
    return rows


def _build_dimensions(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """按 17 个风险维度聚合命中项（仅输出命中的维度，顺序固定）。"""
    grouped: dict[str, list[dict[str, Any]]] = {}
    for finding in findings:
        grouped.setdefault(finding["dimension_key"], []).append(finding)

    dimensions: list[dict[str, Any]] = []
    for dimension in DIMENSIONS:
        items = grouped.get(dimension.key)
        if not items:
            continue

        stats = {"high": 0, "medium": 0, "low": 0, "total": len(items)}
        for item in items:
            stats[item["severity_group"]] += 1

        rule_ids = sorted({item["rule_id"] for item in items if item["rule_id"]})
        remediations: list[str] = []
        for item in sorted(items, key=_issue_sort_key):
            if item["remediation"] and item["remediation"] not in remediations:
                remediations.append(item["remediation"])

        dimensions.append(
            {
                "key": dimension.key,
                "name": dimension.name,
                "category_key": dimension.category_key,
                "description": dimension.description,
                "rule_ids": rule_ids,
                "rules": _build_rule_rows(items),
                "stats": stats,
                "max_severity_group": next(
                    group for group in ("high", "medium", "low") if stats[group]
                ),
                "remediation": "；".join(remediations) if remediations else None,
            }
        )
    return dimensions


def build_audit_report(skill: Any, audit: Any | None) -> dict[str, Any]:
    """构造风险评估报告响应体（含 has_report 标记）。

    ``skill`` / ``audit`` 为 ORM 对象；``audit`` 为 None 表示尚无审计记录。
    """
    base: dict[str, Any] = {
        "skill_id": getattr(skill, "skill_id", ""),
        "skill_name": getattr(skill, "name", "") or "",
        "source_url": getattr(skill, "source_url", None),
        "repo_url": getattr(skill, "repo_url", None),
        "version": getattr(skill, "version", None),
        "has_report": False,
        "reason": None,
        "generated_at": None,
        "engine": None,
        "engine_version": None,
        "score": None,
        "level": None,
        "level_label": None,
        "level_description": None,
        "recommendation": None,
        "summary": None,
        "rule_count": RULE_COUNT,
        "stats": None,
        "categories": [],
        "dimensions": [],
        "findings": [],
        "findings_truncated": False,
    }

    if audit is None:
        base["reason"] = "no_audit"
        return base

    details = getattr(audit, "details", None) or {}
    base["generated_at"] = getattr(audit, "audited_at", None)
    base["engine"] = "NVIDIA SkillSpector"
    base["engine_version"] = details.get("skillspector_version") or None

    report = details.get("skillspector_report") or {}
    if not isinstance(report, dict) or not report:
        base["reason"] = "report_unavailable"
        return base

    issues = [issue for issue in (report.get("issues") or []) if isinstance(issue, dict)]

    score = _resolve_score(details, report, skill)
    level, level_label, level_description = _level_from_score(score)

    findings = sorted((_build_finding(issue) for issue in issues), key=_issue_sort_key)
    stats = {"high": 0, "medium": 0, "low": 0, "total": len(findings)}
    for finding in findings:
        stats[finding["severity_group"]] += 1

    dimensions = _build_dimensions(findings)

    categories = []
    for category in CATEGORIES:
        category_stats = {"high": 0, "medium": 0, "low": 0, "total": 0}
        for finding in findings:
            if _dimension_group_key(finding["dimension_key"]) == category.key:
                category_stats[finding["severity_group"]] += 1
                category_stats["total"] += 1
        categories.append(
            {
                "key": category.key,
                "name": category.name,
                "description": category.description,
                "dimension_count": len(category.dimensions),
                "dimensions": [
                    {
                        "key": key,
                        "name": DIMENSION_BY_KEY[key].name if key in DIMENSION_BY_KEY else key,
                    }
                    for key in category.dimensions
                ],
                "stats": category_stats,
            }
        )

    truncated = len(findings) > MAX_FINDINGS
    base.update(
        {
            "has_report": True,
            "score": score,
            "level": level,
            "level_label": level_label,
            "level_description": level_description,
            "recommendation": details.get("recommendation")
            or (report.get("risk_assessment") or {}).get("recommendation"),
            "summary": _build_summary(score, level, level_label, stats),
            "stats": stats,
            "categories": categories,
            "dimensions": dimensions,
            "findings": findings[:MAX_FINDINGS],
            "findings_truncated": truncated,
        }
    )
    return base