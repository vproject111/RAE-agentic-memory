import httpx
import os
import structlog

logger = structlog.get_logger(__name__)

class RAESuiteClient:
    """
    Unified API Client for RAE Portal.
    Enforces Tenant Isolation and Project Context.
    """
    def __init__(self, api_url=None, tenant_id=None, token=None):
        # Default to standard production values
        self.api_url = api_url or os.getenv("RAE_API_URL", "http://rae-api-dev:8000")
        self.tenant_id = tenant_id or os.getenv("RAE_TENANT_ID", "66435998-b1d9-5521-9481-55a9fd10e014")
        self.token = token
        self.timeout = 300.0 # Increased for CPU-heavy QWEN 3.5

    def _get_headers(self, extra=None):
        headers = {
            "X-Tenant-Id": self.tenant_id,
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if extra:
            headers.update(extra)
        return headers

    async def execute_agent(self, prompt, project="default", model=None, mode="procedural"):
        """Calls AGIS v3.0 logic with specific reasoning mode."""
        url = f"{self.api_url}/v2/agent/execute"
        headers = self._get_headers({"Content-Type": "application/json"})
        payload = {
            "prompt": prompt,
            "project": project,
            "metadata": {
                "llm_model": model,
                "mode": mode # analytical vs procedural
            }
        }
        async with httpx.AsyncClient() as client:
            try:
                r = await client.post(url, json=payload, headers=headers, timeout=self.timeout)
                if r.status_code == 200:
                    return r.json()
                return {"answer": f"Error {r.status_code}: {r.text[:200]}"}
            except Exception as e:
                logger.error("agent_execution_failed", error=str(e), project=project)
                return {"answer": f"Connection Error: {str(e)}"}

    async def get_stats(self, project="default"):
        """Fetches knowledge base statistics for specific project context."""
        url = f"{self.api_url}/v2/memories/stats?project={project}"
        headers = self._get_headers()
        async with httpx.AsyncClient() as client:
            try:
                r = await client.get(url, headers=headers, timeout=10.0)
                return r.json()
            except Exception:
                return {"total_count": 0}

    async def ingest_text(self, text, project="default", source="portal_upload"):
        """Universal text ingestion into specific context."""
        url = f"{self.api_url}/v2/memories/"
        headers = self._get_headers()
        payload = {
            "content": text,
            "project": project,
            "source": source,
            "importance": 0.7,
            "tags": ["portal_ingest"]
        }
        async with httpx.AsyncClient() as client:
            try:
                r = await client.post(url, json=payload, headers=headers, timeout=60.0)
                return r.status_code in [200, 201]
            except Exception as e:
                logger.error("ingestion_failed", error=str(e))
                return False
