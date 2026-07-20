import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from apps.memory_api.models.dashboard_models import AuditTrailEntry
from apps.memory_api.services.rae_core_service import RAECoreService

logger = logging.getLogger(__name__)


class AuditService:
    """
    ISO/IEC 42001 & ISO 27001 Compliance Audit Service.
    Handles audit trail logging, integrity verification, and access controls.
    """

    def __init__(self, rae_service: RAECoreService):
        self.rae_service = rae_service

    def verify_memory_hash(self, content: str, stored_hash: str) -> bool:
        """Verify that memory content matches the stored cryptographic hash."""
        if not content or not stored_hash:
            return False
        calculated = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return calculated == stored_hash

    def mask_secrets(self, text: str) -> str:
        """Redact sensitive credentials, API keys, and connection strings."""
        if not text:
            return text
        patterns = [
            (r"(sk-or-v1-[a-zA-Z0-9]{64})", "[MASKED_OPENROUTER_KEY]"),
            (r"(sk-[a-zA-Z0-9]{20,})", "[MASKED_API_KEY]"),
            (
                r"(password\s*[:=]\s*['\"][^'\"]+['\"])",
                "password = '[MASKED_PASSWORD]'",
            ),
            (
                r"(db_password\s*[:=]\s*['\"][^'\"]+['\"])",
                "db_password = '[MASKED_PASSWORD]'",
            ),
            (r"(Bearer\s+[a-zA-Z0-9\-\._~\+\/]+=*)", "Bearer [MASKED_TOKEN]"),
        ]
        masked = text
        for pattern, replacement in patterns:
            masked = re.sub(pattern, replacement, masked, flags=re.IGNORECASE)
        return masked

    async def log_access(
        self,
        tenant_id: str,
        user_id: str,
        action: str,
        resource: str,
        resource_id: Optional[str] = None,
        allowed: bool = True,
        denial_reason: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Log access attempt to critical compliance resources."""
        try:
            sql = """
                INSERT INTO public.access_logs (
                    id, tenant_id, user_id, action, resource, resource_id,
                    allowed, denial_reason, ip_address, user_agent, timestamp, metadata
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            """
            # Ensure tenant_id is UUID
            tenant_uuid = (
                UUID(tenant_id)
                if isinstance(tenant_id, str) and "-" in tenant_id
                else uuid4()
            )
            await self.rae_service.db.execute(
                sql,
                uuid4(),
                tenant_uuid,
                user_id,
                action,
                resource,
                resource_id,
                allowed,
                denial_reason,
                ip_address,
                user_agent,
                datetime.now(timezone.utc),
                metadata or {},
            )
        except Exception as e:
            logger.error(f"Failed to write access log: {e}", exc_info=True)

    async def get_audit_trail(
        self,
        tenant_id: str,
        project: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        event_types: Optional[List[str]] = None,
        actor_types: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0,
        request_user_id: str = "system_auditor",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Retrieve keyset-compatible paginated list of audit trail entries.
        Performs server-side integrity check and secret masking.
        """
        # Log this audit access
        await self.log_access(
            tenant_id=tenant_id,
            user_id=request_user_id,
            action="read_audit_trail",
            resource="audit_trail",
            allowed=True,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"project": project},
        )

        entries = []
        total_count = 0

        # Query memories representing system/agent decisions
        memories_query = """
            SELECT id, tenant_id, content, source, project, session_id, agent_id, info_class, governance, created_at, content_hash, human_label
            FROM public.memories
            WHERE (tenant_id = $1 OR tenant_id = (SELECT tenant_id::text FROM public.tenants WHERE name = $1 LIMIT 1))
              AND ($2::timestamp IS NULL OR created_at >= $2)
              AND ($3::timestamp IS NULL OR created_at <= $3)
            ORDER BY created_at DESC, id DESC
            LIMIT $4 OFFSET $5
        """

        count_query = """
            SELECT COUNT(*)
            FROM public.memories
            WHERE (tenant_id = $1 OR tenant_id = (SELECT tenant_id::text FROM public.tenants WHERE name = $1 LIMIT 1))
              AND ($2::timestamp IS NULL OR created_at >= $2)
              AND ($3::timestamp IS NULL OR created_at <= $3)
        """

        try:
            total_count = (
                await self.rae_service.db.fetchval(
                    count_query, tenant_id, start_time, end_time
                )
                or 0
            )
            rows = await self.rae_service.db.fetch(
                memories_query, tenant_id, start_time, end_time, limit, offset
            )

            for row in rows:
                content = row["content"]
                stored_hash = row["content_hash"]

                # Crytographic verification
                hash_verified = (
                    self.verify_memory_hash(content, stored_hash)
                    if stored_hash
                    else False
                )

                # Secret masking
                masked_content = self.mask_secrets(content)
                governance = row["governance"] or {}
                if "failure_trace" in governance and governance["failure_trace"]:
                    governance["failure_trace"] = self.mask_secrets(
                        governance["failure_trace"]
                    )

                # Map to model
                entry = AuditTrailEntry(
                    entry_id=row["id"],
                    tenant_id=tenant_id,
                    event_type=(
                        "memory_ingestion"
                        if row["source"] == "user-input"
                        else "model_decision"
                    ),
                    event_category=(
                        "data_operation"
                        if row["source"] == "user-input"
                        else "ai_decision"
                    ),
                    actor_type="user" if row["source"] == "user-input" else "system",
                    actor_id=row["agent_id"] or "default_agent",
                    actor_name=row["agent_id"] or "Default Agent",
                    resource_type="memory",
                    resource_id=str(row["id"]),
                    resource_name=row["human_label"]
                    or row["project"]
                    or "Unnamed Memory",
                    action="create",
                    action_description=(
                        masked_content[:200] + "..."
                        if len(masked_content) > 200
                        else masked_content
                    ),
                    result="success",
                    result_details="Hash Verified: " + str(hash_verified),
                    session_id=row["session_id"],
                    timestamp=row["created_at"].replace(tzinfo=timezone.utc),
                    metadata={
                        "info_class": row["info_class"],
                        "hash_verified": hash_verified,
                        "governance": governance,
                        "project": row["project"],
                    },
                )
                entries.append(entry)

            # Completeness rating based on verified hashes percentage
            verified_count = sum(
                1 for e in entries if e.metadata.get("hash_verified") is True
            )
            completeness = (verified_count / len(entries) * 100) if entries else 100.0

            return {
                "entries": entries,
                "total_count": total_count,
                "completeness_percentage": completeness,
            }

        except Exception as e:
            logger.error(f"Failed to query compliance audit trail: {e}", exc_info=True)
            raise e
