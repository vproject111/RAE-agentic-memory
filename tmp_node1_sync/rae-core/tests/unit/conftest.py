import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest


@pytest.fixture
def golden_snapshot(request: Any) -> Any:
    """Fixture to record and verify golden snapshots for Rust migration."""

    def _record(
        test_name: str,
        inputs: dict[str, Any],
        output: Any,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        snapshot = {
            "test_name": test_name,
            "inputs": inputs,
            "output": output,
            "metadata": metadata or {},
        }

        # Ensure directory exists relative to PROJECT_ROOT
        # We assume we are running from project root
        golden_dir = Path("rae-core/tests/golden")
        golden_dir.mkdir(parents=True, exist_ok=True)

        file_path = golden_dir / f"{test_name}.json"
        with open(file_path, "w") as f:
            # Handle non-serializable objects (like UUIDs)
            def serializer(obj: Any) -> str:
                if isinstance(obj, UUID):
                    return str(obj)
                if isinstance(obj, datetime):
                    return obj.isoformat()
                raise TypeError(f"Type {type(obj)} not serializable")

            json.dump(snapshot, f, indent=2, default=serializer)

    return _record
