from __future__ import annotations

import asyncio
import logging
from typing import Any

from rae_core.interfaces.adapter import (
    AdapterPayloadTooLargeError,
    AdapterTimeoutError,
    AdapterUnavailableError,
    IKnowledgeAdapter,
    RetrievalContext,
    RetrievedKnowledge,
)

logger = logging.getLogger(__name__)


class AdapterBroker:
    def __init__(
        self,
        adapters: list[IKnowledgeAdapter[Any]],
        *,
        max_concurrency: int = 8,
    ) -> None:
        self._adapters = {adapter.adapter_id: adapter for adapter in adapters}
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def retrieve(
        self,
        query: str,
        *,
        context: RetrievalContext[Any],
        adapter_ids: list[str] | None = None,
        limit_per_adapter: int = 5,
    ) -> list[RetrievedKnowledge]:
        if not query.strip():
            raise ValueError("Zapytanie nie może być puste")
        if not 1 <= limit_per_adapter <= 100:
            raise ValueError("Niepoprawny limit")

        selected_ids = adapter_ids or list(self._adapters)
        if len(selected_ids) * limit_per_adapter > 500:
            raise ValueError("Przekroczony maksymalny limit wyników (max 500)")

        missing = [item for item in selected_ids if item not in self._adapters]
        if missing:
            raise ValueError(f"Nieznane adaptery: {sorted(missing)}")

        async def fetch(
            adapter: IKnowledgeAdapter[Any],
        ) -> list[RetrievedKnowledge]:
            try:
                async with self._semaphore:
                    async with asyncio.timeout(context.timeout_seconds):
                        return await adapter.retrieve(
                            query,
                            limit=limit_per_adapter,
                            context=context,
                        )
            except TimeoutError:
                logger.warning(
                    "Adapter timeout",
                    extra={
                        "adapter_id": adapter.adapter_id,
                        "tenant_id": context.tenant_id,
                        "request_id": context.request_id,
                    },
                )
            except (
                AdapterTimeoutError,
                AdapterUnavailableError,
                AdapterPayloadTooLargeError,
            ) as exc:
                logger.warning(
                    "Adapter unavailable",
                    extra={
                        "adapter_id": adapter.adapter_id,
                        "error": type(exc).__name__,
                        "tenant_id": context.tenant_id,
                        "request_id": context.request_id,
                    },
                )
            except Exception:
                logger.exception(
                    "Unexpected adapter failure",
                    extra={"adapter_id": adapter.adapter_id},
                )
            return []

        async with asyncio.TaskGroup() as group:
            tasks = [
                group.create_task(fetch(self._adapters[adapter_id]))
                for adapter_id in selected_ids
            ]

        merged = [item for task in tasks for item in task.result()]
        return self._deduplicate(merged)

    @staticmethod
    def _deduplicate(
        items: list[RetrievedKnowledge],
    ) -> list[RetrievedKnowledge]:
        selected: dict[tuple[str, str], RetrievedKnowledge] = {}
        for item in items:
            key = (item.checksum, item.source_ref)
            current = selected.get(key)
            if current is None or item.score > current.score:
                selected[key] = item
        return list(selected.values())
