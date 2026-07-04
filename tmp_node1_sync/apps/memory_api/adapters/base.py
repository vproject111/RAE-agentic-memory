from abc import ABC, abstractmethod
from typing import Any, Dict

from apps.memory_api.core.contract import ValidationResult


class MemoryAdapter(ABC):
    """
    Abstract base class for memory adapters.
    Defines the interface for validating different memory layers (e.g., Postgres, Redis, Qdrant).
    """

    @abstractmethod
    async def connect(self) -> None:
        """
        Establishes a connection to the memory layer.
        """
        pass

    @abstractmethod
    async def validate(self, contract: Any) -> ValidationResult:
        """
        Validates the memory layer against the provided contract.

        Args:
            contract: The contract object defining the expected state of the memory layer.

        Returns:
            A ValidationResult object containing validation results.
        """
        pass

    @abstractmethod
    async def report(self) -> Dict[str, Any]:
        """
        Generates a report on the current state and configuration of the memory layer.

        Returns:
            A dictionary containing the report data.
        """
        pass
