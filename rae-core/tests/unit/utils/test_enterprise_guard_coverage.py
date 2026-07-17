from unittest.mock import MagicMock

import pytest

from rae_core.utils.enterprise_guard import (
    FatalEnterpriseError,
    RAE_Enterprise_Foundation,
    audited_operation,
)


class MockModule:
    def __init__(self):
        self.enterprise_foundation = RAE_Enterprise_Foundation(
            module_name="test-module"
        )

    @audited_operation(operation_name="test_async_op", impact_level="high")
    async def test_async_method(self, arg):
        return f"async-{arg}"

    @audited_operation(operation_name="test_sync_op")
    def test_sync_method(self, arg):
        return f"sync-{arg}"


class TestEnterpriseGuard:
    def test_foundation_init(self):
        foundation = RAE_Enterprise_Foundation(module_name="test-module")
        assert foundation.module_name == "test-module"
        assert foundation.bridge is not None

    @pytest.mark.asyncio
    async def test_audited_operation_async(self):
        obj = MockModule()
        obj.enterprise_foundation.bridge.save_event = MagicMock()

        result = await obj.test_async_method("data")

        assert result == "async-data"
        assert obj.enterprise_foundation.bridge.save_event.call_count >= 2

    @pytest.mark.asyncio
    async def test_audited_operation_sync(self):
        obj = MockModule()
        obj.enterprise_foundation.bridge.save_event = MagicMock()

        # In our implementation, sync methods decorated with audited_operation
        # return a coroutine because the internal audit is async.
        coro = obj.test_sync_method("data")
        result = await coro

        assert result == "sync-data"
        assert obj.enterprise_foundation.bridge.save_event.call_count >= 2

    def test_verify_contract_violation(self):
        foundation = RAE_Enterprise_Foundation(module_name="test-module")
        with pytest.raises(FatalEnterpriseError):
            foundation.verify_contract("hack", "use nano to edit files")

    def test_verify_contract_success(self):
        foundation = RAE_Enterprise_Foundation(module_name="test-module")
        assert foundation.verify_contract("clean_op", "use cat to read") is True
