from typing import List

import httpx
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever


class _RAEAPIClient:
    """A simple client for the RAE Memory API."""

    def __init__(self, tenant_id: str, api_key: str, base_url: str):
        self.tenant_id = tenant_id
        self.headers = {"X-API-Key": api_key, "X-Tenant-Id": tenant_id}
        self.base_url = f"{base_url}/v1"

    def query(self, query: str, k: int = 4) -> List[Document]:
        """Queries the RAE API and returns a list of LangChain Documents."""
        payload = {"query_text": query, "k": k}
        try:
            with httpx.Client() as client:
                response = client.post(
                    f"{self.base_url}/memory/query", json=payload, headers=self.headers
                )
                response.raise_for_status()

                results = response.json().get("results", [])
                documents = []
                for res in results:
                    metadata = {
                        "source": res.get("source"),
                        "score": res.get("score"),
                        "layer": res.get("layer"),
                        "timestamp": res.get("timestamp"),
                    }
                    documents.append(
                        Document(page_content=res.get("content", ""), metadata=metadata)
                    )
                return documents
        except httpx.HTTPStatusError as e:
            print(f"Error querying RAE API: {e.response.text}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
        return []


class RAERetriever(BaseRetriever):
    """
    A LangChain retriever that fetches relevant documents from the RAE Memory Engine.
    """

    client: _RAEAPIClient
    k: int = 4  # Number of documents to retrieve

    class Config:
        arbitrary_types_allowed = True

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[Document]:
        """
        Retrieves relevant documents from the RAE API.

        Args:
            query: The user's query text.

        Returns:
            A list of LangChain Document objects.
        """
        return self.client.query(query=query, k=self.k)
