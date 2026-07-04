from typing import Any, Dict

import pytest

from apps.memory_api.core.contract import (
    MemoryContract,
    ValidationResult,
    ValidationViolation,
)
from apps.memory_api.core.contract_definition import RAE_MEMORY_CONTRACT_V1
from apps.memory_api.services.validation_service import ValidationService
from rae_adapters.base import MemoryAdapter


# Mock Adapters for testing ValidationService
class MockAdapterSuccess(MemoryAdapter):
    def __init__(self, name: str = "MockAdapterSuccess"):
        self._name = name

    async def connect(self) -> None:
        pass  # Always succeeds

    async def validate(self, contract: MemoryContract) -> ValidationResult:
        return ValidationResult(valid=True, violations=[])

    async def report(self) -> Dict[str, Any]:
        return {"status": "ok", "name": self._name}


class MockAdapterFailValidation(MemoryAdapter):
    def __init__(self, name: str = "MockAdapterFailValidation"):
        self._name = name

    async def connect(self) -> None:
        pass

    async def validate(self, contract: MemoryContract) -> ValidationResult:
        return ValidationResult(
            valid=False,
            violations=[
                ValidationViolation(
                    entity=self._name,
                    issue_type="TEST_VIOLATION",
                    details=f"Test violation from {self._name}",
                )
            ],
        )

    async def report(self) -> Dict[str, Any]:
        return {"status": "ok", "name": self._name}


class MockAdapterFailConnect(MemoryAdapter):
    def __init__(self, name: str = "MockAdapterFailConnect"):
        self._name = name

    async def connect(self) -> None:
        raise ConnectionError(f"Failed to connect to {self._name}")

    async def validate(self, contract: MemoryContract) -> ValidationResult:
        return ValidationResult(valid=True, violations=[])  # Should not be called

    async def report(self) -> Dict[str, Any]:
        return {"status": "error", "name": self._name, "details": "Connect failed"}


@pytest.mark.asyncio
async def test_validation_service_all_success():
    adapter1 = MockAdapterSuccess("Adapter1")
    adapter2 = MockAdapterSuccess("Adapter2")
    service = ValidationService([adapter1, adapter2])

    result = await service.validate_all(RAE_MEMORY_CONTRACT_V1)
    assert result.valid is True
    assert len(result.violations) == 0


@pytest.mark.asyncio
async def test_validation_service_one_adapter_fails_validation():
    adapter1 = MockAdapterSuccess("Adapter1")
    adapter2 = MockAdapterFailValidation("Adapter2")
    service = ValidationService([adapter1, adapter2])

    result = await service.validate_all(RAE_MEMORY_CONTRACT_V1)
    assert result.valid is False
    assert len(result.violations) == 1
    assert result.violations[0].entity == "Adapter2"
    assert result.violations[0].issue_type == "TEST_VIOLATION"


@pytest.mark.asyncio
async def test_validation_service_one_adapter_fails_connect():
    adapter1 = MockAdapterSuccess("Adapter1")
    adapter2 = MockAdapterFailConnect("Adapter2")
    service = ValidationService([adapter1, adapter2])

    result = await service.validate_all(RAE_MEMORY_CONTRACT_V1)
    assert result.valid is False
    assert len(result.violations) == 1
    assert result.violations[0].entity == "Adapter2"
    assert result.violations[0].issue_type == "CONNECTION_OR_VALIDATION_ERROR"
    assert "Failed to connect to Adapter2" in result.violations[0].details


@pytest.mark.asyncio
async def test_validation_service_get_reports_success():
    adapter1 = MockAdapterSuccess("Adapter1")
    adapter2 = MockAdapterSuccess("Adapter2")
    service = ValidationService([adapter1, adapter2])

    reports = await service.get_reports()
    assert reports["Adapter1"]["name"] == "Adapter1"
    assert reports["Adapter2"]["name"] == "Adapter2"
    assert reports["Adapter1"]["status"] == "ok"
    assert reports["Adapter2"]["status"] == "ok"


@pytest.mark.asyncio
async def test_validation_service_get_reports_with_failure():
    adapter1 = MockAdapterSuccess("Adapter1")
    adapter2 = MockAdapterFailConnect("Adapter2")
    service = ValidationService([adapter1, adapter2])

    reports = await service.get_reports()
    assert reports["Adapter1"]["name"] == "Adapter1"
    assert reports["Adapter2"]["status"] == "error"
    assert "Connect failed" in reports["Adapter2"]["details"]
