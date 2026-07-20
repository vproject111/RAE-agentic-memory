import os

import httpx
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
        self.tenant_id = tenant_id or os.getenv(
            "RAE_TENANT_ID", "66435998-b1d9-5521-9481-55a9fd10e014"
        )
        self.token = token
        self.timeout = 300.0  # Increased for CPU-heavy QWEN 3.5

    def _get_headers(self, extra=None):
        headers = {
            "X-Tenant-Id": self.tenant_id,
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if extra:
            headers.update(extra)
        return headers

    async def execute_agent(
        self, prompt, project="default", model=None, mode="procedural"
    ):
        """Calls AGIS v3.0 logic with specific reasoning mode."""
        url = f"{self.api_url}/v2/agent/execute"
        headers = self._get_headers({"Content-Type": "application/json"})
        payload = {
            "prompt": prompt,
            "project": project,
            "metadata": {"llm_model": model, "mode": mode},  # analytical vs procedural
        }
        async with httpx.AsyncClient() as client:
            try:
                r = await client.post(
                    url, json=payload, headers=headers, timeout=self.timeout
                )
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
            "tags": ["portal_ingest"],
        }
        async with httpx.AsyncClient() as client:
            try:
                r = await client.post(url, json=payload, headers=headers, timeout=60.0)
                return r.status_code in [200, 201]
            except Exception as e:
                logger.error("ingestion_failed", error=str(e))
                return False

    async def get_compliance_report(
        self, project="default", report_type="full", include_audit_trail=True
    ):
        """Fetches ISO 42001 / ISO 27001 compliance report."""
        url = f"{self.api_url}/v2/dashboard/compliance/report"
        headers = self._get_headers({"Content-Type": "application/json"})
        payload = {
            "tenant_id": self.tenant_id,
            "project": project,
            "report_type": report_type,
            "include_audit_trail": include_audit_trail,
        }
        async with httpx.AsyncClient() as client:
            try:
                r = await client.post(url, json=payload, headers=headers, timeout=30.0)
                if r.status_code == 200:
                    return r.json()
                logger.error(
                    "get_compliance_report_failed",
                    status_code=r.status_code,
                    response=r.text[:200],
                )
                return {}
            except Exception as e:
                logger.error("get_compliance_report_connection_failed", error=str(e))
                return {}

    async def get_compliance_audit_trail(self, project="default", page=1, page_size=20):
        """Fetches compliance audit trail logs."""
        url = f"{self.api_url}/v2/dashboard/compliance/audit-trail?tenant_id={self.tenant_id}&project={project}&page={page}&page_size={page_size}"
        headers = self._get_headers()
        async with httpx.AsyncClient() as client:
            try:
                r = await client.get(url, headers=headers, timeout=10.0)
                if r.status_code == 200:
                    return r.json()
                return {"items": []}
            except Exception as e:
                logger.error("get_compliance_audit_trail_failed", error=str(e))
                return {"items": []}

    async def get_rls_status(self):
        """Fetches RLS status from the database security checks."""
        url = f"{self.api_url}/v2/dashboard/compliance/rls-status?tenant_id={self.tenant_id}"
        headers = self._get_headers()
        async with httpx.AsyncClient() as client:
            try:
                r = await client.get(url, headers=headers, timeout=10.0)
                if r.status_code == 200:
                    return r.json()
                return {}
            except Exception as e:
                logger.error("get_rls_status_failed", error=str(e))
                return {}

    async def create_mesh_invite(self, host_url: str):
        url = f"{self.api_url}/v2/mesh/invite"
        headers = self._get_headers({"Content-Type": "application/json"})
        payload = {"host_url": host_url, "tenant_id": self.tenant_id}
        async with httpx.AsyncClient() as client:
            try:
                r = await client.post(url, json=payload, headers=headers, timeout=30.0)
                if r.status_code in [200, 201]:
                    return r.json()
                return {"error": r.text}
            except Exception as e:
                return {"error": str(e)}

    async def join_mesh(self, invite_code: str, my_peer_id: str, my_public_url: str, my_name: str):
        url = f"{self.api_url}/v2/mesh/join"
        headers = self._get_headers({"Content-Type": "application/json"})
        payload = {
            "invite_code": invite_code,
            "my_peer_id": my_peer_id,
            "my_public_url": my_public_url,
            "my_name": my_name
        }
        async with httpx.AsyncClient() as client:
            try:
                r = await client.post(url, json=payload, headers=headers, timeout=60.0)
                if r.status_code in [200, 201]:
                    return r.json()
                return {"error": r.text}
            except Exception as e:
                return {"error": str(e)}

    async def list_mesh_peers(self):
        url = f"{self.api_url}/v2/mesh/peers"
        headers = self._get_headers()
        async with httpx.AsyncClient() as client:
            try:
                r = await client.get(url, headers=headers, timeout=10.0)
                if r.status_code == 200:
                    return r.json()
                return []
            except Exception as e:
                logger.error("list_mesh_peers_failed", error=str(e))
                return []

    async def get_mesh_peer_status(self, peer_id: str):
        url = f"{self.api_url}/v2/mesh/peers/{peer_id}/status"
        headers = self._get_headers()
        async with httpx.AsyncClient() as client:
            try:
                r = await client.get(url, headers=headers, timeout=10.0)
                if r.status_code == 200:
                    return r.json()
                return {"status": "offline", "latency_ms": -1, "sync_stats": {}}
            except Exception as e:
                logger.error("get_mesh_peer_status_failed", error=str(e))
                return {"status": "offline", "latency_ms": -1, "sync_stats": {}}

    async def trigger_mesh_peer_sync(self, peer_id: str):
        url = f"{self.api_url}/v2/mesh/peers/{peer_id}/sync"
        headers = self._get_headers()
        async with httpx.AsyncClient() as client:
            try:
                r = await client.post(url, headers=headers, timeout=120.0)
                if r.status_code in [200, 201]:
                    return r.json()
                return {"error": r.text}
            except Exception as e:
                return {"error": str(e)}

    async def register_mesh_peer(self, peer_id: str, name: str, url: str, token: str, transport_type: str):
        endpoint = f"{self.api_url}/v2/mesh/peers"
        headers = self._get_headers({"Content-Type": "application/json"})
        payload = {
            "peer_id": peer_id,
            "name": name,
            "url": url,
            "token": token,
            "transport_type": transport_type
        }
        async with httpx.AsyncClient() as client:
            try:
                r = await client.post(endpoint, json=payload, headers=headers, timeout=30.0)
                if r.status_code in [200, 201]:
                    return r.json()
                return {"error": r.text}
            except Exception as e:
                return {"error": str(e)}

    async def revoke_mesh_peer(self, peer_id: str):
        url = f"{self.api_url}/v2/mesh/peers/{peer_id}"
        headers = self._get_headers()
        async with httpx.AsyncClient() as client:
            try:
                r = await client.delete(url, headers=headers, timeout=30.0)
                if r.status_code in [200, 201]:
                    return r.json()
                return {"error": r.text}
            except Exception as e:
                return {"error": str(e)}

