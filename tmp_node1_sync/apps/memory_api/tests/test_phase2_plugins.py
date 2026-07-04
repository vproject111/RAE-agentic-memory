"""
Tests for Phase 2 Plugin System
"""

from typing import Any, Dict
from uuid import uuid4

import pytest

from apps.memory_api.plugins.base import (
    Plugin,
    PluginHook,
    PluginMetadata,
    PluginRegistry,
    get_plugin_registry,
)


class MockTestPlugin(Plugin):
    """Mock plugin for unit tests (renamed to avoid pytest collection)"""

    def _create_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="test_plugin",
            version="1.0.0",
            author="Test Author",
            description="Test plugin",
            hooks=[PluginHook.AFTER_MEMORY_CREATE, PluginHook.BEFORE_QUERY],
        )

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.memory_creates: list[tuple[Any, str]] = []
        self.queries: list[str] = []

    async def on_after_memory_create(
        self, tenant_id, memory_id: str, memory_data: Dict[str, Any]
    ):
        self.memory_creates.append((tenant_id, memory_id))

    async def on_before_query(
        self, tenant_id, query: str, params: Dict[str, Any], **kwargs
    ) -> Dict[str, Any]:
        self.queries.append(query)
        params["modified"] = True
        return params

    async def on_after_memory_update(
        self,
        tenant_id,
        memory_id: str,
        old_data: Dict[str, Any],
        new_data: Dict[str, Any],
    ):
        pass

    async def on_before_memory_delete(self, tenant_id, memory_id: str):
        pass

    async def on_after_memory_delete(self, tenant_id, memory_id: str):
        pass

    async def on_after_query(
        self, tenant_id, query: str, results: list[Dict[str, Any]]
    ):
        pass

    async def on_notification(
        self, tenant_id, notification_type: str, data: Dict[str, Any]
    ):
        pass

    async def on_alert(
        self,
        tenant_id,
        alert_type: str,
        severity: str,
        message: str,
        data: Dict[str, Any],
    ):
        pass


class TestPluginMetadata:
    """Test plugin metadata"""

    def test_metadata_creation(self):
        """Test creating plugin metadata"""
        metadata = PluginMetadata(
            name="test",
            version="1.0.0",
            author="Test",
            description="Test plugin",
            hooks=[PluginHook.AFTER_MEMORY_CREATE],
        )

        assert metadata.name == "test"
        assert metadata.version == "1.0.0"
        assert metadata.enabled is True
        assert len(metadata.hooks) == 1

    def test_metadata_to_dict(self):
        """Test metadata serialization"""
        metadata = PluginMetadata(
            name="test",
            version="1.0.0",
            author="Test",
            description="Test plugin",
            hooks=[PluginHook.AFTER_MEMORY_CREATE],
            config={"key": "value"},
        )

        data = metadata.to_dict()

        assert data["name"] == "test"
        assert data["version"] == "1.0.0"
        assert data["config"]["key"] == "value"
        assert "after_memory_create" in data["hooks"]


class TestPluginBase:
    """Test base plugin class"""

    @pytest.mark.asyncio
    async def test_plugin_initialization(self):
        """Test plugin initialization"""
        plugin = MockTestPlugin(config={"test": "value"})

        assert plugin.config["test"] == "value"
        assert plugin.metadata.name == "test_plugin"

        await plugin.initialize()

    @pytest.mark.asyncio
    async def test_plugin_shutdown(self):
        """Test plugin shutdown"""
        plugin = MockTestPlugin()
        await plugin.shutdown()

    @pytest.mark.asyncio
    async def test_plugin_health_check(self):
        """Test plugin health check"""
        plugin = MockTestPlugin()
        health = await plugin.health_check()

        assert health["plugin"] == "test_plugin"
        assert health["status"] == "healthy"
        assert health["enabled"] is True

    @pytest.mark.asyncio
    async def test_hook_execution(self):
        """Test hook method execution"""
        plugin = MockTestPlugin()
        tenant_id = uuid4()

        # Test after_memory_create hook
        await plugin.on_after_memory_create(
            tenant_id=tenant_id, memory_id="mem_123", memory_data={"content": "test"}
        )

        assert len(plugin.memory_creates) == 1
        assert plugin.memory_creates[0] == (tenant_id, "mem_123")

    @pytest.mark.asyncio
    async def test_transform_hook(self):
        """Test transform hook that modifies data"""
        plugin = MockTestPlugin()
        tenant_id = uuid4()

        params = {"query": "test"}
        modified = await plugin.on_before_query(
            tenant_id=tenant_id, query="search query", params=params
        )

        assert modified["modified"] is True
        assert len(plugin.queries) == 1


class TestPluginRegistry:
    """Test plugin registry"""

    def test_registry_creation(self):
        """Test creating a registry"""
        registry = PluginRegistry()
        assert len(registry._plugins) == 0

    def test_register_plugin(self):
        """Test registering a plugin"""
        registry = PluginRegistry()
        plugin = MockTestPlugin()

        registry.register(plugin)

        assert "test_plugin" in registry._plugins
        assert registry.get("test_plugin") == plugin

    def test_unregister_plugin(self):
        """Test unregistering a plugin"""
        registry = PluginRegistry()
        plugin = MockTestPlugin()

        registry.register(plugin)
        assert "test_plugin" in registry._plugins

        registry.unregister("test_plugin")
        assert "test_plugin" not in registry._plugins

    def test_list_plugins(self):
        """Test listing plugins"""
        registry = PluginRegistry()
        plugin = MockTestPlugin()

        registry.register(plugin)

        plugins = registry.list_plugins()
        assert len(plugins) == 1
        assert plugins[0].name == "test_plugin"

    def test_get_plugins_for_hook(self):
        """Test getting plugins for specific hook"""
        registry = PluginRegistry()
        plugin = MockTestPlugin()

        registry.register(plugin)

        # Plugin handles these hooks
        create_plugins = registry.get_plugins_for_hook(PluginHook.AFTER_MEMORY_CREATE)
        assert len(create_plugins) == 1
        assert create_plugins[0] == plugin

        query_plugins = registry.get_plugins_for_hook(PluginHook.BEFORE_QUERY)
        assert len(query_plugins) == 1

        # Plugin doesn't handle this hook
        delete_plugins = registry.get_plugins_for_hook(PluginHook.AFTER_MEMORY_DELETE)
        assert len(delete_plugins) == 0

    @pytest.mark.asyncio
    async def test_initialize_all(self):
        """Test initializing all plugins"""
        registry = PluginRegistry()
        plugin1 = MockTestPlugin()
        plugin2 = MockTestPlugin()

        registry.register(plugin1)
        registry.register(plugin2)

        await registry.initialize_all()

    @pytest.mark.asyncio
    async def test_shutdown_all(self):
        """Test shutting down all plugins"""
        registry = PluginRegistry()
        plugin = MockTestPlugin()

        registry.register(plugin)
        await registry.shutdown_all()

    @pytest.mark.asyncio
    async def test_execute_hook(self):
        """Test executing a hook"""
        registry = PluginRegistry()
        plugin = MockTestPlugin()
        registry.register(plugin)

        tenant_id = uuid4()

        # Execute hook
        await registry.execute_hook(
            PluginHook.AFTER_MEMORY_CREATE,
            tenant_id=tenant_id,
            memory_id="mem_123",
            memory_data={"content": "test"},
        )

        # Verify plugin received the hook
        assert len(plugin.memory_creates) == 1

    @pytest.mark.asyncio
    async def test_execute_transform_hook(self):
        """Test executing a transform hook"""
        registry = PluginRegistry()
        plugin = MockTestPlugin()
        registry.register(plugin)

        tenant_id = uuid4()
        params = {"original": True}

        # Execute transform hook
        await registry.execute_hook(
            PluginHook.BEFORE_QUERY, tenant_id=tenant_id, query="test", params=params
        )

        # Verify hook was called
        assert len(plugin.queries) == 1
        assert plugin.queries[0] == "test"

    @pytest.mark.asyncio
    async def test_health_check_all(self):
        """Test health checking all plugins"""
        registry = PluginRegistry()
        plugin = MockTestPlugin()
        registry.register(plugin)

        health = await registry.health_check_all()

        assert "test_plugin" in health
        assert health["test_plugin"]["status"] == "healthy"

    def test_get_global_registry(self):
        """Test getting global registry instance"""
        registry1 = get_plugin_registry()
        registry2 = get_plugin_registry()

        # Should be the same instance
        assert registry1 is registry2


class TestPluginHooks:
    """Test plugin hook enum"""

    def test_hook_values(self):
        """Test hook enum values"""
        assert PluginHook.BEFORE_MEMORY_CREATE.value == "before_memory_create"
        assert PluginHook.AFTER_MEMORY_CREATE.value == "after_memory_create"
        assert PluginHook.BEFORE_QUERY.value == "before_query"
        assert PluginHook.AFTER_QUERY.value == "after_query"
        assert PluginHook.NOTIFICATION.value == "notification"
        assert PluginHook.ALERT.value == "alert"

    def test_all_hooks_defined(self):
        """Test that all expected hooks are defined"""
        expected_hooks = [
            "before_memory_create",
            "after_memory_create",
            "before_memory_update",
            "after_memory_update",
            "before_memory_delete",
            "after_memory_delete",
            "before_query",
            "after_query",
            "query_results_transform",
            "before_reflection",
            "after_reflection",
            "before_consolidation",
            "after_consolidation",
            "notification",
            "alert",
            "startup",
            "shutdown",
            "health_check",
        ]

        hook_values = [hook.value for hook in PluginHook]

        for expected in expected_hooks:
            assert expected in hook_values


class TestPluginDisabling:
    """Test plugin enable/disable functionality"""

    def test_disabled_plugin_not_executed(self):
        """Test that disabled plugins are not executed"""
        registry = PluginRegistry()
        plugin = MockTestPlugin()

        # Disable plugin before registering
        plugin.metadata.enabled = False

        registry.register(plugin)

        # Get plugins for hook
        plugins = registry.get_plugins_for_hook(PluginHook.AFTER_MEMORY_CREATE)

        # Should not include disabled plugin
        assert len(plugins) == 0

    @pytest.mark.asyncio
    async def test_disabled_plugin_not_initialized(self):
        """Test that disabled plugins are not initialized"""
        registry = PluginRegistry()
        plugin = MockTestPlugin()

        # Disable before registering
        plugin.metadata.enabled = False
        registry.register(plugin)

        # Should still be in registry but not initialized
        await registry.initialize_all()


class TestMultiplePlugins:
    """Test multiple plugins working together"""

    @pytest.mark.asyncio
    async def test_multiple_plugins_same_hook(self):
        """Test multiple plugins handling same hook"""
        registry = PluginRegistry()
        plugin1 = MockTestPlugin()
        plugin2 = MockTestPlugin()

        registry.register(plugin1)
        registry.register(plugin2)

        tenant_id = uuid4()

        # Execute hook
        await registry.execute_hook(
            PluginHook.AFTER_MEMORY_CREATE,
            tenant_id=tenant_id,
            memory_id="mem_123",
            memory_data={"content": "test"},
        )

        # Both plugins should have received the hook
        assert len(plugin1.memory_creates) == 1
        assert len(plugin2.memory_creates) == 1

    @pytest.mark.asyncio
    async def test_plugin_chaining(self):
        """Test plugins chaining transformations"""
        registry = PluginRegistry()

        # Create plugins with different names to avoid overwriting
        class TestPlugin1(MockTestPlugin):
            @property
            def metadata(self):
                meta = super().metadata
                meta.name = "test_plugin_1"
                return meta

        class TestPlugin2(MockTestPlugin):
            @property
            def metadata(self):
                meta = super().metadata
                meta.name = "test_plugin_2"
                return meta

        plugin1 = TestPlugin1()
        plugin2 = TestPlugin2()

        registry.register(plugin1)
        registry.register(plugin2)

        tenant_id = uuid4()
        params: dict[str, Any] = {}

        # Execute transform hook
        await registry.execute_hook(
            PluginHook.BEFORE_QUERY, tenant_id=tenant_id, query="test", params=params
        )

        # Both plugins should have been called
        assert len(plugin1.queries) == 1
        assert len(plugin2.queries) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
