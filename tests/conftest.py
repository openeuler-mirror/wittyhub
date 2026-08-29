import asyncio

import pytest


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _dispose_db_engine():
    """Dispose the shared async engine after each test.

    `async_engine` is a module-level singleton with a connection pool. Each
    `TestClient(app)` request (without a context manager) runs on its own
    event loop, so a pooled connection created on a previous loop gets reused
    on the next one and asyncpg raises "Future attached to a different loop".
    Disposing the pool forces every test to open fresh connections on its own
    loop.
    """
    yield
    from src.core.database import async_engine

    try:
        asyncio.run(async_engine.dispose())
    except Exception:
        # A previous test may have failed mid-request, leaving pool state
        # that cannot be cleanly closed from this loop — ignore and let the
        # next test start with an empty pool.
        pass
