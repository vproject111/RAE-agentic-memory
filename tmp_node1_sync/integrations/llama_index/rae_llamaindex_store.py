import os
from typing import Any, List, Optional

import httpx
from llama_index.schema import BaseNode, TextNode
from llama_index.vector_stores.types import (
    VectorStore,
    VectorStoreQuery,
    VectorStoreQueryResult,
)


class _RAEAPIClient:
    """A simple client for the RAE Memory API."""

    def __init__(self, tenant_id: str, api_key: str, base_url: str):
        self.tenant_id = tenant_id
        self.headers = {"X-API-Key": api_key, "X-Tenant-Id": tenant_id}
        self.base_url = f"{base_url}/v1"

    def add(self, nodes: List[BaseNode]):
        """Adds a list of nodes to the RAE memory."""
        for node in nodes:
            payload = {
                "content": node.get_content(),
                "source": node.metadata.get("source", "llama_index"),
                "project": node.metadata.get("project", "default"),
                "tags": node.metadata.get("tags", ["llama_index"]),
            }
            try:
                with httpx.Client() as client:
                    client.post(
                        f"{self.base_url}/memory/store",
                        json=payload,
                        headers=self.headers,
                    ).raise_for_status()
            except Exception as e:
                print(f"Error storing node {node.node_id}: {e}")

    def delete(self, ref_doc_id: str, **delete_kwargs: Any):
        """Deletes a document by its ID."""
        try:
            with httpx.Client() as client:
                client.delete(
                    f"{self.base_url}/memory/delete?memory_id={ref_doc_id}",
                    headers=self.headers,
                ).raise_for_status()
        except Exception as e:
            print(f"Error deleting memory {ref_doc_id}: {e}")

    def query(self, query: VectorStoreQuery) -> VectorStoreQueryResult:
        """Queries the RAE API and returns results."""
        payload = {"query_text": query.query_str, "k": query.similarity_top_k}
        try:
            with httpx.Client() as client:
                response = client.post(
                    f"{self.base_url}/memory/query", json=payload, headers=self.headers
                )
                response.raise_for_status()

                results = response.json().get("results", [])
                nodes, similarities, ids = [], [], []
                for res in results:
                    metadata = {"source": res.get("source"), "layer": res.get("layer")}
                    nodes.append(
                        TextNode(text=res.get("content", ""), metadata=metadata)
                    )
                    similarities.append(res.get("score"))
                    ids.append(res.get("id"))

                return VectorStoreQueryResult(
                    nodes=nodes, similarities=similarities, ids=ids
                )
        except Exception as e:
            print(f"Error querying RAE API: {e}")
        return VectorStoreQueryResult(nodes=[], similarities=[], ids=[])


class RAEVectorStore(VectorStore):
    """
    A LlamaIndex VectorStore that uses the RAE Memory Engine as a backend.
    """

    stores_text: bool = True

    def __init__(
        self,
        tenant_id: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        **kwargs: Any,
    ):
        self._client = _RAEAPIClient(
            tenant_id=tenant_id,
            api_key=api_key or os.environ.get("RAE_API_KEY", ""),
            base_url=base_url or os.environ.get("RAE_API_URL", "http://localhost:8000"),
        )

    @property
    def client(self) -> Any:
        return self._client

    def add(self, nodes: List[BaseNode], **add_kwargs: Any) -> List[str]:
        """Adds a list of nodes to the RAE memory."""
        self._client.add(nodes)
        return [node.node_id for node in nodes]

    def delete(self, ref_doc_id: str, **delete_kwargs: Any) -> None:
        """Deletes a document by its ID."""
        self._client.delete(ref_doc_id)

    def query(self, query: VectorStoreQuery, **kwargs: Any) -> VectorStoreQueryResult:
        """Queries the RAE API."""
        return self._client.query(query)
