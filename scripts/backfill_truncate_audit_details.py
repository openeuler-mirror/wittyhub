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
                "SELECT id, details FROM security_audits "
                "WHERE details ? 'skillspector_report'"
            )
        ).all()
        print(f"Found {len(rows)} row(s) storing a skillspector_report")

        updated = 0
        skipped = 0
        for audit_id, details in rows:
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
                print(
                    f"[dry-run] audit {audit_id}: {before} -> {after} bytes "
                    f"(save {before - after})"
                )
                continue
            session.execute(
                text("UPDATE security_audits SET details = :details WHERE id = :id"),
                {"details": details, "id": audit_id},
            )
            updated += 1

        if not args.dry_run:
            session.commit()
            print(f"Updated {updated} row(s); {skipped} row(s) below threshold")
        else:
            print(
                f"Dry-run finished: {updated} candidate row(s) would change; "
                f"{skipped} row(s) below threshold untouched"
            )
    finally:
        session.close()


if __name__ == "__main__":
    main()
