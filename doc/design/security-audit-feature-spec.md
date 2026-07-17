# 安全审计功能设计说明书

## 一、功能概述

安全审计在 Skill 入库后自动触发，对 Skill 源码执行深度扫描：

| 扫描层 | 引擎 | 检测内容 |
|------|------|------|
| 深度审计 | Skillspector（Jenkins Job） | 代码意图分析、风险评分、LLM 辅助检测 |

扫描结果写入 `skills.security_score` 和 `security_audits` 表，前端通过 API 查询渲染安全报告。

---

## 二、总开关

```yaml
# config.yaml
security:
  enable_audit: true   # 关闭则跳过全部审计
```

---

## 三、完整审计链路

### 3.1 同步模式（API 创建 Skill）

```
POST /skills/

routes/skills.py : create_skill()
  │
  ├── SkillRepository.create()              ← 入库（纯数据写入，不触发审计）
  │
  ├── enable_audit == false ──▶ 返回（security_score = NULL）
  │
  └── enable_audit == true
        │
        ▼
  SecurityService.audit_skill()
    │
    ├── scanners 默认: 自动检测
    │     ├── has_skillspector → ["skillspector"]
    │     └── 否则 → []（无可用扫描器）
    │
    ├── Skillspector（已配置时）
    │     SkillspectorClient.run_scan()
    │       ├── POST Jenkins /buildWithParameters
    │       ├── 轮询 build 状态（每5秒，最多150秒）
    │       ├── GET /artifact/reports/skillspector/report.json
    │       └── report_to_risk_signals()
    │     → security_score = report.risk_assessment.score
    │
    └── 持久化（audit_skill 内部完成）
          ├── INSERT security_audits（风险信号 + 完整 report.json）
          ├── UPDATE skills.security_score
          └── COMMIT

routes/skills.py
  └── 返回 SkillResponse（security_score 已由 audit_skill 写入）
```

### 3.2 异步模式

```
async_mode=True

SkillspectorClient.trigger_scan()
  └── POST Jenkins /buildWithParameters → fire-and-forget
       details 记录: { skillspector_async: true, skillspector_build_number: N }

后台: SkillspectorCollector（每 30s，仅 enable_audit=true + 凭证已配时启动）
  ├── 查询 pending audits（skillspector_async=true, collected=null）
  ├── wait_for_build(N)
  ├── fetch_report(N)
  └── 回写 skills.security_score + security_audits
```

启动: `src/security/detector.py` → `start_skillspector_collector()`，由 `src/api/main.py` lifespan 调用。

### 3.3 手动触发

```
POST /skills/{skill_id}/audit?scanners=skillspector
```

调用 `SecurityService.audit_skill()` 重新扫描并返回最新 `SecurityAuditResponse`。

---

## 四、模块架构

```
src/security/detector.py          ← 唯一核心（扫描逻辑 + Collector 工厂函数）
  ├── SecurityDetector             ← 总入口
  ├── SkillspectorClient           ← Jenkins HTTP 交互
  ├── SkillspectorCollector        ← 后台异步回写
  └── start_skillspector_collector()  ← 工厂函数，由 main.py 调用

src/api/services/security.py      ← 编排层
  └── SecurityService.audit_skill()

src/api/routes/skills.py          ← 业务入口
  ├── create_skill()              ← POST /skills/        先入库 → 再审计
  ├── trigger_skill_audit()       ← POST /skills/{id}/audit  手动触发
  └── audit_skill()               ← GET  /skills/{id}/audit  查询结果

src/models/repository.py
  ├── SkillRepository.create()    ← 纯数据写入，不触发审计
  ├── SkillRepository.update()    ← 审计结果回写 security_score
  └── SecurityAuditRepository     ← security_audits 表 CRUD

src/api/main.py                   ← lifespan 调用 start_skillspector_collector()
```

---

## 五、数据库表

### 5.1 skills.security_score

| 字段 | 类型 | 说明 |
|------|------|------|
| `security_score` | `INTEGER` | 0=critical → 100=safe。未审计时为 `NULL` |

### 5.2 security_audits

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `UUID` | 主键 |
| `resource_type` | `VARCHAR(20)` | 固定 `"skill"` |
| `resource_id` | `UUID` | `skills.id` 外键 |
| `version` | `VARCHAR(50)` | Skill 版本号 |
| `commit_id` | `VARCHAR(40)` | Git commit |
| `audit_type` | `VARCHAR(50)` | 扫描器组合：`skillspector`；无扫描时 `none` |
| `risk_level` | `VARCHAR(20)` | `critical` / `high` / `medium` / `low` / `unknown` |
| `risk_signals` | `JSONB` | 风险信号数组 |
| `details` | `JSONB` | 扫描元数据 + 完整 report.json |
| `audited_at` | `TIMESTAMPTZ` | 审计时间 |

**details 结构**:

```json
{
    "scanners": ["skillspector"],
    "skillspector_score": 85,
    "skillspector_version": "2.3.1",
    "recommendation": "SAFE",
    "skillspector_report": { /* Jenkins 返回的完整 report.json，供前端渲染 */ }
}
```

**索引**: `(resource_type, resource_id)`, `risk_level`, `audited_at DESC`, `(resource_id, version, commit_id)`

---

## 六、对外 API 接口

### 6.1 创建 Skill（自动审计）

```
POST /api/v1/skills/
```

请求体 → `SkillCreate schema`。`enable_audit=true` 时入库后自动触发审计，`security_score` 由 `audit_skill()` 写入并返回。审计失败不影响入库。

### 6.2 查询审计结果

```
GET /api/v1/skills/{skill_id}/audit
```

返回最近一次审计记录，无记录返回 `{"error": "No audit found"}`。

### 6.3 手动触发审计

```
POST /api/v1/skills/{skill_id}/audit
```

| Query 参数 | 类型 | 必填 | 说明 |
|------|------|:---:|------|
| `scanners` | `str` | 否 | `skillspector`。默认自动检测可用扫描器 |

**返回** `SecurityAuditResponse`:

```json
{
    "id": "uuid",
    "resource_type": "skill",
    "resource_id": "uuid",
    "version": "v1.0.0",
    "commit_id": "abc1234",
    "audit_type": "skillspector",
    "risk_level": "low",
    "risk_signals": [
        {
            "id": "SQP-1",
            "name": "Skillspector SQP-1 (SKILL.md:12)",
            "description": "Skill references external API...",
            "severity": "MEDIUM",
            "data": {
                "confidence": 0.6,
                "location": { "file": "SKILL.md", "start_line": 12, "end_line": 19 },
                "remediation": "...",
                "source": "skillspector"
            }
        }
    ],
    "details": {
        "scanners": ["skillspector"],
        "skillspector_score": 85,
        "skillspector_version": "2.3.1",
        "recommendation": "SAFE",
        "skillspector_report": { /* Jenkins 原始 report.json，前端直接渲染 */ }
    },
    "audited_at": "2026-07-14T12:00:00Z"
}
```

### 6.4 SecurityService.audit_skill() 内部接口

```python
async def audit_skill(
    skill_id: str,                        # skill 唯一标识
    source: str,                          # "github" / "gitcode" / "clawhub"
    source_url: str,                      # 仓库 URL
    metadata: dict[str, Any],             # { version, content, skill_path }
    scanners: list[str] | None = None,    # None → 自动检测可用扫描器
    async_mode: bool = False,             # True → skillspector fire-and-forget
) -> dict[str, Any]:
```

**返回**:

```json
{
    "risk_level": "low",
    "risk_signals": [
        { "id": "...", "name": "...", "description": "...", "severity": "..." }
    ],
    "security_score": 75,
    "scanners": ["skillspector"]
}
```

---

## 七、评分计算

| 来源 | 规则 |
|------|------|
| Skillspector | 直接使用 `report.risk_assessment.score`（0-100） |
| 无可用扫描器 | `risk_level = unknown` → `security_score = 100` |
| 降级（Jenkins 不可用） | `risk_level = unknown` → `security_score = 100` |

---

## 八、Jenkins Job 参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `GIT_URL` | `str` | Git 仓库 URL |
| `REF` | `str` | 分支/Tag/Commit，默认 `main` |
| `SKILL_PATH` | `str` | Skill 在仓库中的相对路径 |
| `SCANNERS` | `str` | 逗号分隔扫描器列表，默认 `skillspector` |

产物: `reports/skillspector/report.json` + `report.md`

---

## 九、配置项

| 配置 | 环境变量 | 说明 |
|------|------|------|
| `enable_audit` | — | 总开关，yaml 配置 |
| `skillspector_jenkins_url` | `SKILLSPECTOR_JENKINS_URL` | Jenkins 地址 |
| `skillspector_jenkins_user` | `SKILLSPECTOR_JENKINS_USER` | Basic Auth 用户名 |
| `skillspector_jenkins_token` | `SKILLSPECTOR_JENKINS_TOKEN` | Basic Auth Token |

---

## 十、设计原则

| # | 原则 | 说明 |
|---|------|------|
| 1 | **入库与审计分离** | `SkillRepository.create()` 只做数据写入；`routes/skills.py` 在入库后调用 `SecurityService.audit_skill()` 触发审计 |
| 2 | **skill_repo_id 自动推导** | 无 `skill_repo_id` 时从 `source_url` 自动解析 `repo_name`，查重或新建 `SkillRepoModel` |
| 3 | **只读展示** | `GET /audit` 仅返回已存储结果，不触发新扫描 |
| 4 | **降级容错** | 无可用扫描器或 Jenkins 不可用时，降级为 `risk_level=unknown`，审计失败不影响入库 |
| 5 | **异步优先** | 批量场景用 `async_mode`，后台 `SkillspectorCollector` 每 30s 轮询回写 |
