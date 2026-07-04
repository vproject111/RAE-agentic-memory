"""
Data models for RAE Memory API
"""

# Import core models from the models.py file in parent directory
# Using importlib to avoid circular import issues
import importlib.util
from pathlib import Path

from apps.memory_api.models.hybrid_search_models import HybridSearchResult, QueryIntent

# Import Phase 2 models from submodules (early import to avoid E402)
from apps.memory_api.models.rbac import Permission, Role, UserRole
from apps.memory_api.models.tenant import Tenant, TenantConfig, TenantTier

# Load models from the legacy models.py file
models_file = Path(__file__).parent.parent / "models.py"
spec = importlib.util.spec_from_file_location("rae_models_legacy", models_file)
if spec is not None:
    models_legacy = importlib.util.module_from_spec(spec)
    if spec.loader is not None:
        spec.loader.exec_module(models_legacy)
    else:
        raise ImportError(f"Could not load loader for {models_file}")
else:
    raise ImportError(f"Could not find spec for {models_file}")

# Import core models from legacy models.py (only those that exist)
MemoryLayer = models_legacy.MemoryLayer
SourceTrustLevel = models_legacy.SourceTrustLevel
OperationRiskLevel = models_legacy.OperationRiskLevel
MemoryRecord = models_legacy.MemoryRecord
ScoredMemoryRecord = models_legacy.ScoredMemoryRecord
StoreMemoryRequest = models_legacy.StoreMemoryRequest
StoreMemoryResponse = models_legacy.StoreMemoryResponse
QueryMemoryRequest = models_legacy.QueryMemoryRequest
QueryMemoryResponse = models_legacy.QueryMemoryResponse
DeleteMemoryRequest = models_legacy.DeleteMemoryRequest
DeleteMemoryResponse = models_legacy.DeleteMemoryResponse
RebuildReflectionsRequest = models_legacy.RebuildReflectionsRequest
AgentExecuteRequest = models_legacy.AgentExecuteRequest
CostInfo = models_legacy.CostInfo
AgentExecuteResponse = models_legacy.AgentExecuteResponse
ListMemoryResponse = models_legacy.ListMemoryResponse

__all__ = [
    # Core models
    "MemoryLayer",
    "SourceTrustLevel",
    "OperationRiskLevel",
    "MemoryRecord",
    "ScoredMemoryRecord",
    "StoreMemoryRequest",
    "StoreMemoryResponse",
    "QueryMemoryRequest",
    "QueryMemoryResponse",
    "ListMemoryResponse",
    "DeleteMemoryRequest",
    "DeleteMemoryResponse",
    "RebuildReflectionsRequest",
    "AgentExecuteRequest",
    "CostInfo",
    "AgentExecuteResponse",
    # Phase 2 models
    "Tenant",
    "TenantTier",
    "TenantConfig",
    "Role",
    "Permission",
    "UserRole",
    # Hybrid Search Models
    "HybridSearchResult",
    "QueryIntent",
]
