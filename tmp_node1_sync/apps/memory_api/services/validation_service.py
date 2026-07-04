import logging
from typing import Any, Dict, List

from apps.memory_api.core.contract import (
    MemoryContract,
    ValidationResult,
    ValidationViolation,
)
from rae_adapters.base import MemoryAdapter

logger = logging.getLogger(__name__)


class ValidationService:
    def __init__(self, adapters: List[MemoryAdapter]):
        self.adapters = adapters

    async def validate_all(self, contract: MemoryContract) -> ValidationResult:
        all_violations: List[ValidationViolation] = []
        is_valid = True

        for adapter in self.adapters:
            adapter_key = getattr(adapter, "_name", adapter.__class__.__name__)
            adapter_name = adapter.__class__.__name__
            try:
                logger.info(f"Connecting to {adapter_name}...")
                await adapter.connect()
                logger.info(f"Connected to {adapter_name}. Running validation...")
                result = await adapter.validate(contract)

                if not result.valid:
                    is_valid = False
                    all_violations.extend(result.violations)
                    logger.error(
                        f"Validation failed for {adapter_name}: {result.violations}"
                    )
                else:
                    logger.info(f"Validation successful for {adapter_name}.")
            except Exception as e:
                is_valid = False
                violation = ValidationViolation(
                    entity=adapter_key,
                    issue_type="CONNECTION_OR_VALIDATION_ERROR",
                    details=f"Failed to connect or validate: {str(e)}",
                )
                all_violations.append(violation)
                logger.error(f"Error with {adapter_name}: {e}")

        return ValidationResult(valid=is_valid, violations=all_violations)

    async def get_reports(self) -> Dict[str, Any]:
        all_reports: Dict[str, Any] = {}
        for adapter in self.adapters:
            adapter_key = getattr(adapter, "_name", adapter.__class__.__name__)
            try:
                report_data = await adapter.report()
                all_reports[adapter_key] = report_data
            except Exception as e:
                logger.error(f"Failed to get report from {adapter_key}: {e}")
                all_reports[adapter_key] = {"status": "error", "details": str(e)}
        return all_reports
