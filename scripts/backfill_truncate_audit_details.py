#!/usr/bin/env python3
"""Backfill: truncate oversized ``code_snippet`` in existing security_audits rows.

New audits are already compressed at write time by ``_maybe_compress_details``
(only when the ``details`` estimate exceeds 1MB). This one-time script applies
the same rule to rows that were stored before that change.

Usage:
    python scripts/backfill_truncate_audit_details.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402

from src.core.database import SyncSessionLocal  # noqa: E402
from src.security.detector import MAX_DETAILS_BYTES, SNIPPET_MAX_CHARS  # noqa: E402


def _estimate_bytes(details: dict) -> int:
    return len(json.dumps(details, ensure_ascii=False).encode("utf-8"))


def _truncate_snippets(details: dict) -> bool:
    """Same rule as _maybe_compress_details; returns True when anything changed."""
    if _estimate_bytes(details) <= MAX_DETAILS_BYTES:
        return False

    report = details.get("skillspector_report")
    if not isinstance(report, dict):
        return False

    changed = False
    for issue in report.get("issues") or []:
        if not isinstance(issue, dict):
            continue
        # 幂等防护：已截断过的 issue（写入时压缩或此前回填）直接跳过，
        # 避免截断后片段（500 字 + 后缀 > 500）被反复重截、mangling 后缀
        if issue.get("truncated"):
            continue
        snippet = issue.get("code_snippet")
        if isinstance(snippet, str) and len(snippet) > SNIPPET_MAX_CHARS:
            issue["code_snippet"] = snippet[:SNIPPET_MAX_CHARS] + (
                f"\n... [truncated, original {len(snippet)} chars]"
            )
            issue["truncated"] = True
            changed = True
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would change without updating rows",
    )
    args = parser.parse_args()

    session = SyncSessionLocal()
    try:
        rows = session.execute(
            text(
                "SELECT id, audited_at, details FROM security_audits "
                "WHERE details ? 'skillspector_report'"
            )
        ).all()
        print(f"Found {len(rows)} row(s) storing a skillspector_report")

        updated = 0
        skipped = 0
        raced = 0
        for audit_id, audited_at, details in rows:
            if not isinstance(details, dict):
                continue
            before = _estimate_bytes(details)
            if before <= MAX_DETAILS_BYTES:
                skipped += 1
                continue
            changed = _truncate_snippets(details)
            if not changed:
                continue
            after = _estimate_bytes(details)
            if args.dry_run:
                updated += 1  # dry-run 也计入候选行数，保证汇总数字与逐行输出一致
                print(
                    f"[dry-run] audit {audit_id}: {before} -> {after} bytes "
                    f"(save {before - after})"
                )
                continue
            result = session.execute(
                text(
                    "UPDATE security_audits SET details = CAST(:details AS jsonb) "
                    "WHERE id = :id AND audited_at IS NOT DISTINCT FROM :audited_at"
                ),
                {
                    # psycopg2 不能直接适配 dict，需先序列化为 JSON 字符串再交给 PG 转换
                    "details": json.dumps(details, ensure_ascii=False),
                    "id": audit_id,
                    # 乐观锁：SELECT 后该行若被并发扫描重新审计（audited_at 变化），
                    # 则放弃更新，避免用旧数据的截断版覆盖新鲜审计结果
                    "audited_at": audited_at,
                },
            )
            if result.rowcount:
                updated += 1
            else:
                raced += 1

        if not args.dry_run:
            session.commit()
            print(
                f"Updated {updated} row(s); {raced} row(s) raced with concurrent "
                f"re-audit (skipped); {skipped} row(s) below threshold"
            )
        else:
            print(
                f"Dry-run finished: {updated} candidate row(s) would change; "
                f"{skipped} row(s) below threshold untouched"
            )
    finally:
        session.close()


if __name__ == "__main__":
    main()
