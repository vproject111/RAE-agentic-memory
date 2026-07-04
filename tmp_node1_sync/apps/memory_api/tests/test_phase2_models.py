"""
Tests for Phase 2 Models (Multi-tenancy and RBAC)
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from apps.memory_api.models.rbac import Permission, Role, RoleHierarchy, UserRole
from apps.memory_api.models.tenant import Tenant, TenantConfig, TenantTier


class TestTenantModels:
    """Test tenant models"""

    def test_tenant_tier_enum(self):
        """Test tenant tier enum values"""
        assert TenantTier.FREE.value == "free"
        assert TenantTier.PRO.value == "pro"
        assert TenantTier.ENTERPRISE.value == "enterprise"

    def test_tenant_config_defaults(self):
        """Test tenant config default values"""
        config = TenantConfig()
        assert config.max_memories == 10000
        assert config.max_projects == 5
        assert config.enable_reflection is True
        assert config.enable_graphrag is False

    def test_tenant_creation(self):
        """Test tenant creation"""
        tenant_id = uuid4()
        tenant = Tenant(
            id=tenant_id,
            name="Test Tenant",
            tier=TenantTier.PRO,
            contact_email="test@example.com",
        )

        assert tenant.id == tenant_id
        assert tenant.name == "Test Tenant"
        assert tenant.tier == TenantTier.PRO
        assert tenant.status == "active"
        assert tenant.current_memory_count == 0

    def test_get_default_config_for_free_tier(self):
        """Test default config for FREE tier"""
        config = Tenant.get_default_config_for_tier(TenantTier.FREE)

        assert config.max_memories == 10000
        assert config.max_projects == 3
        assert config.enable_graphrag is False
        assert config.enable_analytics is False
        assert config.encryption_enabled is False

    def test_get_default_config_for_pro_tier(self):
        """Test default config for PRO tier"""
        config = Tenant.get_default_config_for_tier(TenantTier.PRO)

        assert config.max_memories == 100000
        assert config.max_projects == 10
        assert config.enable_graphrag is True
        assert config.enable_analytics is True
        assert config.encryption_enabled is True

    def test_get_default_config_for_enterprise_tier(self):
        """Test default config for ENTERPRISE tier"""
        config = Tenant.get_default_config_for_tier(TenantTier.ENTERPRISE)

        assert config.max_memories == -1  # Unlimited
        assert config.max_projects == -1  # Unlimited
        assert config.enable_graphrag is True
        assert config.enable_analytics is True
        assert config.sso_enabled is True
        assert config.audit_log_enabled is True

    def test_has_quota_available_memories(self):
        """Test quota checking for memories"""
        tenant = Tenant(
            id=uuid4(),
            name="Test",
            tier=TenantTier.FREE,
            config=TenantConfig(max_memories=100),
        )

        # Below quota
        tenant.current_memory_count = 50
        assert tenant.has_quota_available("memories") is True

        # At quota
        tenant.current_memory_count = 99
        assert tenant.has_quota_available("memories") is True

        # Over quota
        tenant.current_memory_count = 100
        assert tenant.has_quota_available("memories") is False

    def test_has_quota_available_unlimited(self):
        """Test quota checking with unlimited quota"""
        tenant = Tenant(
            id=uuid4(),
            name="Test",
            tier=TenantTier.ENTERPRISE,
            config=TenantConfig(max_memories=-1),
        )

        tenant.current_memory_count = 999999
        assert tenant.has_quota_available("memories") is True

    def test_increment_usage(self):
        """Test usage increment"""
        tenant = Tenant(id=uuid4(), name="Test", tier=TenantTier.FREE)

        assert tenant.current_memory_count == 0
        tenant.increment_usage("memories", 5)
        assert tenant.current_memory_count == 5

        tenant.increment_usage("memories")
        assert tenant.current_memory_count == 6

    def test_is_feature_enabled(self):
        """Test feature enablement check"""
        tenant = Tenant(
            id=uuid4(),
            name="Test",
            tier=TenantTier.PRO,
            config=TenantConfig(enable_graphrag=True, enable_analytics=True),
        )

        assert tenant.is_feature_enabled("graphrag") is True
        assert tenant.is_feature_enabled("analytics") is True
        assert tenant.is_feature_enabled("nonexistent") is False


class TestRBACModels:
    """Test RBAC models"""

    def test_role_enum_values(self):
        """Test role enum values"""
        assert Role.OWNER.value == "owner"
        assert Role.ADMIN.value == "admin"
        assert Role.DEVELOPER.value == "developer"
        assert Role.ANALYST.value == "analyst"
        assert Role.VIEWER.value == "viewer"

    def test_role_levels(self):
        """Test role privilege levels"""
        assert Role.OWNER.level == 5
        assert Role.ADMIN.level == 4
        assert Role.DEVELOPER.level == 3
        assert Role.ANALYST.level == 2
        assert Role.VIEWER.level == 1

    def test_role_can_perform_owner(self):
        """Test OWNER permissions"""
        assert Role.OWNER.can_perform("anything") is True
        assert Role.OWNER.can_perform("memories:write") is True
        assert Role.OWNER.can_perform("users:delete") is True

    def test_role_can_perform_admin(self):
        """Test ADMIN permissions"""
        assert Role.ADMIN.can_perform("users:write") is True
        assert Role.ADMIN.can_perform("settings:write") is True
        assert Role.ADMIN.can_perform("memories:write") is True
        assert Role.ADMIN.can_perform("billing:read") is True

    def test_role_can_perform_developer(self):
        """Test DEVELOPER permissions"""
        assert Role.DEVELOPER.can_perform("memories:write") is True
        assert Role.DEVELOPER.can_perform("graph:write") is True
        assert Role.DEVELOPER.can_perform("reflections:read") is True
        assert Role.DEVELOPER.can_perform("users:write") is False
        assert Role.DEVELOPER.can_perform("billing:read") is False

    def test_role_can_perform_analyst(self):
        """Test ANALYST permissions"""
        assert Role.ANALYST.can_perform("memories:read") is True
        assert Role.ANALYST.can_perform("analytics:read") is True
        assert Role.ANALYST.can_perform("graph:read") is True
        assert Role.ANALYST.can_perform("memories:write") is False

    def test_role_can_perform_viewer(self):
        """Test VIEWER permissions"""
        assert Role.VIEWER.can_perform("memories:read") is True
        assert Role.VIEWER.can_perform("memories:write") is False
        assert Role.VIEWER.can_perform("analytics:read") is False

    def test_permission_model(self):
        """Test permission model"""
        perm = Permission(resource="memories", action="write")
        assert str(perm) == "memories:write"

    def test_user_role_creation(self):
        """Test user role creation"""
        user_role = UserRole(
            id=uuid4(),
            user_id="user_123",
            tenant_id=uuid4(),
            role=Role.DEVELOPER,
            assigned_by="admin_user",
        )

        assert user_role.user_id == "user_123"
        assert user_role.role == Role.DEVELOPER
        assert user_role.is_expired() is False

    def test_user_role_expiration(self):
        """Test user role expiration"""
        # Expired role
        expired_role = UserRole(
            id=uuid4(),
            user_id="user_123",
            tenant_id=uuid4(),
            role=Role.DEVELOPER,
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        assert expired_role.is_expired() is True

        # Active role
        active_role = UserRole(
            id=uuid4(),
            user_id="user_123",
            tenant_id=uuid4(),
            role=Role.DEVELOPER,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        assert active_role.is_expired() is False

        # No expiration
        no_expiry = UserRole(
            id=uuid4(), user_id="user_123", tenant_id=uuid4(), role=Role.DEVELOPER
        )
        assert no_expiry.is_expired() is False

    def test_user_role_project_access(self):
        """Test project-scoped access"""
        # No project restriction
        user_role = UserRole(
            id=uuid4(),
            user_id="user_123",
            tenant_id=uuid4(),
            role=Role.DEVELOPER,
            project_ids=[],
        )
        assert user_role.has_access_to_project("any_project") is True

        # With project restriction
        user_role = UserRole(
            id=uuid4(),
            user_id="user_123",
            tenant_id=uuid4(),
            role=Role.DEVELOPER,
            project_ids=["project_1", "project_2"],
        )
        assert user_role.has_access_to_project("project_1") is True
        assert user_role.has_access_to_project("project_2") is True
        assert user_role.has_access_to_project("project_3") is False

    def test_user_role_can_perform(self):
        """Test user role permission checking"""
        user_role = UserRole(
            id=uuid4(), user_id="user_123", tenant_id=uuid4(), role=Role.DEVELOPER
        )

        assert user_role.can_perform("memories:write") is True
        assert user_role.can_perform("users:write") is False

    def test_user_role_can_perform_with_project(self):
        """Test permission checking with project scope"""
        user_role = UserRole(
            id=uuid4(),
            user_id="user_123",
            tenant_id=uuid4(),
            role=Role.DEVELOPER,
            project_ids=["project_1"],
        )

        # Has permission and project access
        assert user_role.can_perform("memories:write", "project_1") is True

        # Has permission but no project access
        assert user_role.can_perform("memories:write", "project_2") is False

    def test_role_hierarchy_comparison(self):
        """Test role hierarchy comparison"""
        assert RoleHierarchy.is_higher_or_equal(Role.OWNER, Role.ADMIN) is True
        assert RoleHierarchy.is_higher_or_equal(Role.ADMIN, Role.DEVELOPER) is True
        assert RoleHierarchy.is_higher_or_equal(Role.DEVELOPER, Role.VIEWER) is True
        assert RoleHierarchy.is_higher_or_equal(Role.VIEWER, Role.ADMIN) is False

    def test_can_assign_role(self):
        """Test role assignment permissions"""
        # Owner can assign any role
        assert RoleHierarchy.can_assign_role(Role.OWNER, Role.ADMIN) is True
        assert RoleHierarchy.can_assign_role(Role.OWNER, Role.VIEWER) is True

        # Admin can assign roles below them
        assert RoleHierarchy.can_assign_role(Role.ADMIN, Role.DEVELOPER) is True
        assert RoleHierarchy.can_assign_role(Role.ADMIN, Role.VIEWER) is True
        assert RoleHierarchy.can_assign_role(Role.ADMIN, Role.ADMIN) is False
        assert RoleHierarchy.can_assign_role(Role.ADMIN, Role.OWNER) is False

        # Others cannot assign roles
        assert RoleHierarchy.can_assign_role(Role.DEVELOPER, Role.VIEWER) is False

    def test_can_modify_user(self):
        """Test user modification permissions"""
        # Can modify lower roles
        assert RoleHierarchy.can_modify_user(Role.OWNER, Role.ADMIN) is True
        assert RoleHierarchy.can_modify_user(Role.ADMIN, Role.DEVELOPER) is True

        # Cannot modify equal or higher roles
        assert RoleHierarchy.can_modify_user(Role.ADMIN, Role.ADMIN) is False
        assert RoleHierarchy.can_modify_user(Role.ADMIN, Role.OWNER) is False
        assert RoleHierarchy.can_modify_user(Role.DEVELOPER, Role.ADMIN) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
