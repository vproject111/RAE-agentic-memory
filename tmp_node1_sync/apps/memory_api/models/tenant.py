"""
Tenant models for multi-tenancy support
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TenantTier(str, Enum):
    """Tenant subscription tiers"""

    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class TenantConfig(BaseModel):
    """Tenant-specific configuration"""

    # Resource Limits
    max_memories: int = Field(default=10000, description="Maximum memories allowed")
    max_projects: int = Field(default=5, description="Maximum projects allowed")
    max_api_calls_per_day: int = Field(
        default=10000, description="Daily API call limit"
    )
    max_storage_mb: int = Field(default=1000, description="Maximum storage in MB")

    # Feature Flags
    enable_graphrag: bool = Field(default=False, description="Enable GraphRAG features")
    enable_analytics: bool = Field(
        default=False, description="Enable analytics dashboard"
    )
    enable_reflection: bool = Field(
        default=True, description="Enable reflection engine"
    )
    enable_multi_modal: bool = Field(
        default=False, description="Enable multi-modal memories"
    )
    custom_embedding_model: bool = Field(
        default=False, description="Allow custom embedding models"
    )

    # Security Settings
    encryption_enabled: bool = Field(
        default=False, description="Enable data encryption at rest"
    )
    audit_log_enabled: bool = Field(default=False, description="Enable audit logging")
    sso_enabled: bool = Field(default=False, description="Enable SSO authentication")
    require_mfa: bool = Field(
        default=False, description="Require multi-factor authentication"
    )

    # Performance Settings
    cache_ttl_seconds: int = Field(default=3600, description="Cache TTL in seconds")
    max_query_results: int = Field(default=100, description="Maximum query results")
    enable_batch_operations: bool = Field(
        default=False, description="Enable batch API operations"
    )

    # LLM Settings
    llm_provider: Optional[str] = Field(
        default=None, description="Preferred LLM provider"
    )
    embedding_model: Optional[str] = Field(
        default=None, description="Preferred embedding model"
    )
    max_llm_calls_per_day: Optional[int] = Field(
        default=None, description="Daily LLM call limit"
    )

    # Retention Settings
    memory_retention_days: int = Field(
        default=365, description="Memory retention period"
    )
    auto_consolidation: bool = Field(
        default=False, description="Enable automatic memory consolidation"
    )


class Tenant(BaseModel):
    """Tenant model with tier-based configuration"""

    id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    tier: TenantTier

    # Configuration
    config: TenantConfig = Field(default_factory=TenantConfig)

    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = Field(
        default="active", description="Tenant status: active, suspended, deleted"
    )

    # Contact Info
    contact_email: Optional[str] = None
    company_name: Optional[str] = None

    # Usage Tracking
    current_memory_count: int = Field(
        default=0, description="Current number of memories"
    )
    current_project_count: int = Field(
        default=0, description="Current number of projects"
    )
    api_calls_today: int = Field(default=0, description="API calls made today")

    # Billing
    subscription_start: Optional[datetime] = None
    subscription_end: Optional[datetime] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Acme Corp",
                "tier": "enterprise",
                "contact_email": "admin@acme.com",
                "config": {
                    "max_memories": 1000000,
                    "enable_graphrag": True,
                    "enable_analytics": True,
                },
            }
        }
    )

    @staticmethod
    def get_default_config_for_tier(tier: TenantTier) -> TenantConfig:
        """Get default configuration based on tier"""

        if tier == TenantTier.FREE:
            return TenantConfig(
                max_memories=10000,
                max_projects=3,
                max_api_calls_per_day=1000,
                max_storage_mb=500,
                enable_graphrag=False,
                enable_analytics=False,
                custom_embedding_model=False,
                encryption_enabled=False,
                audit_log_enabled=False,
                sso_enabled=False,
            )

        elif tier == TenantTier.PRO:
            return TenantConfig(
                max_memories=100000,
                max_projects=10,
                max_api_calls_per_day=10000,
                max_storage_mb=5000,
                enable_graphrag=True,
                enable_analytics=True,
                custom_embedding_model=True,
                encryption_enabled=True,
                audit_log_enabled=False,
                sso_enabled=False,
            )

        else:  # ENTERPRISE
            return TenantConfig(
                max_memories=-1,  # Unlimited
                max_projects=-1,  # Unlimited
                max_api_calls_per_day=-1,  # Unlimited
                max_storage_mb=-1,  # Unlimited
                enable_graphrag=True,
                enable_analytics=True,
                enable_multi_modal=True,
                custom_embedding_model=True,
                encryption_enabled=True,
                audit_log_enabled=True,
                sso_enabled=True,
                require_mfa=True,
                enable_batch_operations=True,
                auto_consolidation=True,
            )

    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled for this tenant"""
        return getattr(self.config, f"enable_{feature}", False)

    def has_quota_available(self, resource: str) -> bool:
        """Check if tenant has quota available for resource"""
        if resource == "memories":
            limit = self.config.max_memories
            current = self.current_memory_count
        elif resource == "projects":
            limit = self.config.max_projects
            current = self.current_project_count
        elif resource == "api_calls":
            limit = self.config.max_api_calls_per_day
            current = self.api_calls_today
        else:
            return True

        # -1 means unlimited
        if limit == -1:
            return True

        return current < limit

    def increment_usage(self, resource: str, amount: int = 1):
        """Increment usage counter for resource"""
        if resource == "memories":
            self.current_memory_count += amount
        elif resource == "projects":
            self.current_project_count += amount
        elif resource == "api_calls":
            self.api_calls_today += amount


class TenantUsageStats(BaseModel):
    """Tenant usage statistics"""

    tenant_id: UUID
    period_start: datetime
    period_end: datetime

    # Resource Usage
    total_memories: int
    memories_by_layer: dict[str, int]
    total_storage_mb: float

    # API Usage
    total_api_calls: int
    api_calls_by_endpoint: dict[str, int]
    avg_response_time_ms: float

    # Feature Usage
    total_queries: int
    total_reflections: int
    graph_nodes_count: int
    graph_edges_count: int

    # Cost Tracking (if applicable)
    llm_api_calls: int
    embedding_api_calls: int
    estimated_cost_usd: Optional[float] = None
