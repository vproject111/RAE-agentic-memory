from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict

from rae_core.interfaces.adapter import (
    IKnowledgeAdapter,
    RetrievalContext,
    RetrievedKnowledge,
    compute_content_checksum,
)
from rae_core.models.knowledge import AuthorityLevel, KnowledgeSourceType


class OpenAPIQueryParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    method_filter: str | None = None


class OpenAPIAdapter(IKnowledgeAdapter[OpenAPIQueryParams]):
    adapter_id = "openapi-specification"
    source_type = KnowledgeSourceType.OPENAPI

    def __init__(self, spec_path: str) -> None:
        self.spec_path = Path(spec_path)
        self.spec_data = self._load_spec()
        self._index = self._build_index(self.spec_data)

    def _load_spec(self) -> dict[str, Any]:
        if not self.spec_path.is_file():
            raise FileNotFoundError(f"Spec path {self.spec_path} is not a file")
        with self.spec_path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
        if not isinstance(data, dict):
            raise ValueError("Specyfikacja OpenAPI musi być obiektem")
        return data

    @staticmethod
    def _build_index(
        spec_data: dict[str, Any],
    ) -> list[tuple[str, dict[str, Any], str]]:
        result = []
        for path, methods in spec_data.get("paths", {}).items():
            if not isinstance(methods, dict):
                continue
            rendered = yaml.safe_dump(
                {path: methods},
                sort_keys=True,
                allow_unicode=True,
            )
            result.append((path, methods, rendered))
        return result

    async def retrieve(
        self,
        query: str,
        *,
        limit: int,
        context: RetrievalContext[OpenAPIQueryParams],
    ) -> list[RetrievedKnowledge]:
        query_lower = query.lower().strip()
        method_filter = (
            context.params.method_filter.lower()
            if context.params and context.params.method_filter
            else None
        )
        results: list[RetrievedKnowledge] = []

        for path, methods, rendered in self._index:
            if method_filter and method_filter not in {
                method.lower() for method in methods
            }:
                continue
            if query_lower not in f"{path}\n{rendered}".lower():
                continue
            if len(rendered.encode("utf-8")) > context.max_response_bytes:
                continue

            results.append(
                RetrievedKnowledge(
                    evidence_id=f"openapi:{path}",
                    content=rendered,
                    source_ref=f"file://{self.spec_path}#/paths{path}",
                    source_type=KnowledgeSourceType.OPENAPI,
                    authority_level=AuthorityLevel.CANONICAL,
                    score=1.0,
                    observed_at=datetime.now(timezone.utc),
                    checksum=compute_content_checksum(rendered),
                    metadata={
                        "path": path,
                        "methods": sorted(methods),
                    },
                )
            )
            if len(results) >= limit:
                break

        await asyncio.sleep(0)
        return results
