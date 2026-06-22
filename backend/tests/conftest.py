"""Pytest conftest for backend tests.

FastAPI lifespan (init_pg_pool/close_pg_pool) is NOT triggered by ASGITransport
for HTTP scopes. The pool is lazily created by get_pg_pool() on first use and
never automatically closed.

With function-scoped event loops, connections from a previous test's loop cause
"attached to a different loop" errors. Since the event loop is closed by the
time teardown runs, we can't close the pool in teardown. Instead, we reset the
pool global to None BEFORE each test, so get_pg_pool() creates a fresh pool in
the current test's event loop. The old pool is leaked but this is fine for tests.
"""

import pytest


@pytest.fixture(autouse=True)
def _reset_pg_pool():
    """Reset PG pool global at start of each test (before event loop is created)."""
    import app.core.pg as pg_module

    pg_module._pool = None  # Leak old pool but get a fresh one per test
    yield
