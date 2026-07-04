"""Coverage tests for database interfaces."""

from rae_core.interfaces.database import (
    IDatabaseConnection,
    IDatabaseProvider,
    ITransaction,
)


def test_database_protocols_runtime_checkable():
    """Verify that protocols are runtime checkable and can be mocked."""

    class MockTransaction:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

        async def commit(self):
            pass

        async def rollback(self):
            pass

    class MockConnection:
        async def execute(self, query, *args):
            return ""

        async def fetch(self, query, *args):
            return []

        async def fetchrow(self, query, *args):
            return {}

        async def fetchval(self, query, *args):
            return None

        async def executemany(self, query, args):
            return ""

        def transaction(self):
            return MockTransaction()

    class MockProvider:
        async def execute(self, query, *args):
            return ""

        async def fetch(self, query, *args):
            return []

        async def fetchrow(self, query, *args):
            return {}

        async def fetchval(self, query, *args):
            return None

        async def executemany(self, query, args):
            return ""

        async def close(self):
            pass

        def acquire(self):
            return MockConnection()

    assert isinstance(MockTransaction(), ITransaction)
    assert isinstance(MockConnection(), IDatabaseConnection)
    assert isinstance(MockProvider(), IDatabaseProvider)
