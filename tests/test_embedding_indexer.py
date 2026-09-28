import argparse
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from scripts import reindex_embeddings
from src.ai import embedding_indexer
from src.ai.embedding_indexer import (
    EmbeddingTarget,
    ReindexStats,
    SkillNotFoundError,
)
from src.models.repository import SkillRepository


def target(skill_id: str, text: str = "text") -> EmbeddingTarget:
    return EmbeddingTarget(
        skill_id=skill_id,
        text=text,
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


class AsyncContext:
    def __init__(self, value):
        self.value = value

    async def __aenter__(self):
        return self.value

    async def __aexit__(self, exc_type, exc, traceback):
        return False


@pytest.mark.asyncio
async def test_run_batches_advances_cursor_after_failed_full_batch(monkeypatch):
    cursors = []

    async def fetch(after_skill_id, limit, only_missing):
        cursors.append(after_skill_id)
        if after_skill_id is None:
            return [target("a"), target("b")]
        return []

    monkeypatch.setattr(embedding_indexer, "_count_targets", AsyncMock(return_value=2))
    monkeypatch.setattr(embedding_indexer, "_fetch_batch", fetch)
    monkeypatch.setattr(
        embedding_indexer,
        "generate_embeddings",
        AsyncMock(side_effect=RuntimeError("service unavailable")),
    )

    stats = ReindexStats()
    await embedding_indexer._run_batches(
        only_missing=True, stats=stats, batch_size=2
    )

    assert cursors == [None, "b"]
    assert stats.failed_batches == 1
    assert stats.failed_rows == 2


@pytest.mark.asyncio
async def test_run_batches_advances_cursor_for_full_empty_text_batch(monkeypatch):
    cursors = []

    async def fetch(after_skill_id, limit, only_missing):
        cursors.append(after_skill_id)
        if after_skill_id is None:
            return [target("a", ""), target("b", " ")]
        return []

    generate = AsyncMock()
    monkeypatch.setattr(embedding_indexer, "_count_targets", AsyncMock(return_value=2))
    monkeypatch.setattr(embedding_indexer, "_fetch_batch", fetch)
    monkeypatch.setattr(embedding_indexer, "generate_embeddings", generate)

    stats = ReindexStats()
    await embedding_indexer._run_batches(
        only_missing=True, stats=stats, batch_size=2
    )

    assert cursors == [None, "b"]
    assert stats.skipped_empty == 2
    generate.assert_not_awaited()


@pytest.mark.parametrize(
    ("embeddings", "message"),
    [
        ([[0.1, 0.2]], "count mismatch"),
        ([[0.1], [0.2]], "dimension mismatch"),
        ([[0.1, float("nan")], [0.2, 0.3]], "non-finite"),
    ],
)
def test_validate_embeddings_rejects_invalid_response(embeddings, message):
    with pytest.raises(ValueError, match=message):
        embedding_indexer._validate_embeddings(
            embeddings, expected_count=2, expected_dimension=2
        )


@pytest.mark.asyncio
async def test_run_batches_counts_stale_write(monkeypatch):
    async def fetch(after_skill_id, limit, only_missing):
        if after_skill_id is None:
            return [target("a")]
        return []

    monkeypatch.setattr(embedding_indexer, "_count_targets", AsyncMock(return_value=1))
    monkeypatch.setattr(embedding_indexer, "_fetch_batch", fetch)
    monkeypatch.setattr(
        embedding_indexer,
        "generate_embeddings",
        AsyncMock(return_value=[[0.0] * 768]),
    )
    monkeypatch.setattr(embedding_indexer, "_write_embeddings", AsyncMock(return_value=0))

    stats = ReindexStats()
    await embedding_indexer._run_batches(
        only_missing=False, stats=stats, batch_size=1
    )

    assert stats.indexed == 0
    assert stats.stale_skipped == 1


@pytest.mark.asyncio
async def test_repository_write_uses_updated_at_guard():
    session = AsyncMock()
    result = MagicMock()
    result.rowcount = 1
    session.execute.return_value = result
    expected_updated_at = datetime(2026, 1, 1, tzinfo=timezone.utc)

    updated = await SkillRepository(session).update_embeddings_batch(
        [("skill-a", expected_updated_at, [0.1, 0.2])]
    )

    statement = session.execute.await_args.args[0]
    sql = str(statement)
    assert "skills.skill_id" in sql
    assert "skills.updated_at" in sql
    assert updated == 1
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_reindex_single_skill_uses_shared_validation_and_write(monkeypatch):
    lock_session = AsyncMock()
    lock_result = MagicMock()
    lock_result.scalar.return_value = True
    lock_session.execute.return_value = lock_result
    monkeypatch.setattr(
        embedding_indexer,
        "AsyncSessionLocal",
        lambda: AsyncContext(lock_session),
    )
    monkeypatch.setattr(
        embedding_indexer, "_fetch_target", AsyncMock(return_value=target("skill-a"))
    )
    monkeypatch.setattr(
        embedding_indexer,
        "generate_embeddings",
        AsyncMock(return_value=[[0.0] * 768]),
    )
    write = AsyncMock(return_value=1)
    monkeypatch.setattr(embedding_indexer, "_write_embeddings", write)

    stats = await embedding_indexer.reindex_skill("skill-a")

    assert stats == ReindexStats(total=1, indexed=1)
    write.assert_awaited_once()
    assert lock_session.execute.await_count == 2


@pytest.mark.asyncio
async def test_reindex_single_skill_reports_not_found_and_unlocks(monkeypatch):
    lock_session = AsyncMock()
    lock_result = MagicMock()
    lock_result.scalar.return_value = True
    lock_session.execute.return_value = lock_result
    monkeypatch.setattr(
        embedding_indexer,
        "AsyncSessionLocal",
        lambda: AsyncContext(lock_session),
    )
    monkeypatch.setattr(
        embedding_indexer, "_fetch_target", AsyncMock(return_value=None)
    )

    with pytest.raises(SkillNotFoundError, match="missing"):
        await embedding_indexer.reindex_skill("missing")

    assert lock_session.execute.await_count == 2


@pytest.mark.parametrize("value", ["0", "-1", "1001"])
def test_cli_rejects_invalid_batch_size(value):
    with pytest.raises(argparse.ArgumentTypeError, match="1 到 1000"):
        reindex_embeddings.batch_size(value)


@pytest.mark.asyncio
async def test_cli_returns_nonzero_for_partial_reindex(monkeypatch):
    monkeypatch.setattr(
        reindex_embeddings,
        "get_settings",
        lambda: SimpleNamespace(
            ai=SimpleNamespace(
                enable_semantic_search=True,
                embedding_host="http://embedding",
                embedding_model="model",
                embedding_dimension=768,
            )
        ),
    )
    monkeypatch.setattr(
        reindex_embeddings,
        "reindex_all",
        AsyncMock(
            return_value=ReindexStats(
                total=2, indexed=1, failed_batches=1, failed_rows=1
            )
        ),
    )
    monkeypatch.setattr("sys.argv", ["reindex_embeddings.py"])

    assert await reindex_embeddings.main() == 4


@pytest.mark.asyncio
async def test_cli_reindexes_only_requested_skill(monkeypatch):
    monkeypatch.setattr(
        reindex_embeddings,
        "get_settings",
        lambda: SimpleNamespace(
            ai=SimpleNamespace(
                enable_semantic_search=True,
                embedding_host="http://embedding",
                embedding_model="model",
                embedding_dimension=768,
            )
        ),
    )
    single = AsyncMock(return_value=ReindexStats(total=1, indexed=1))
    full = AsyncMock()
    monkeypatch.setattr(reindex_embeddings, "reindex_skill", single)
    monkeypatch.setattr(reindex_embeddings, "reindex_all", full)
    monkeypatch.setattr(
        "sys.argv", ["reindex_embeddings.py", "--skill-id", "git:owner/repo/skill"]
    )

    assert await reindex_embeddings.main() == 0
    single.assert_awaited_once_with("git:owner/repo/skill")
    full.assert_not_awaited()
