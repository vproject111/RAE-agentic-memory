"""
Base Plugin System - Core plugin infrastructure
"""

import importlib
import importlib.util
import inspect
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog

logger = structlog.get_logger(__name__)


class PluginHook(str, Enum):
    """Available plugin hooks"""

    # Memory lifecycle hooks
    BEFORE_MEMORY_CREATE = "before_memory_create"
    AFTER_MEMORY_CREATE = "after_memory_create"
    BEFORE_MEMORY_UPDATE = "before_memory_update"
    AFTER_MEMORY_UPDATE = "after_memory_update"
    BEFORE_MEMORY_DELETE = "before_memory_delete"
    AFTER_MEMORY_DELETE = "after_memory_delete"

    # Query hooks
    BEFORE_QUERY = "before_query"
    AFTER_QUERY = "after_query"
    QUERY_RESULTS_TRANSFORM = "query_results_transform"

    # Reflection hooks
    BEFORE_REFLECTION = "before_reflection"
    AFTER_REFLECTION = "after_reflection"
    REFLECTION_TRANSFORM = "reflection_transform"

    # Consolidation hooks
    BEFORE_CONSOLIDATION = "before_consolidation"
    AFTER_CONSOLIDATION = "after_consolidation"

    # Analytics hooks
    METRICS_COLLECTED = "metrics_collected"
    ANALYTICS_REPORT = "analytics_report"

    # System hooks
    STARTUP = "startup"
    SHUTDOWN = "shutdown"
    HEALTH_CHECK = "health_check"

    # Notification hooks
    NOTIFICATION = "notification"
    ALERT = "alert"

    # Custom processing
    CUSTOM_PROCESSOR = "custom_processor"


class PluginMetadata:
    """Plugin metadata and configuration"""

    def __init__(
        self,
        name: str,
        version: str,
        author: str,
        description: str,
        hooks: List[PluginHook],
        enabled: bool = True,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.version = version
        self.author = author
        self.description = description
        self.hooks = hooks
        self.enabled = enabled
        self.config = config or {}
        self.loaded_at: Optional[datetime] = None
        self.error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "hooks": [h.value for h in self.hooks],
            "enabled": self.enabled,
            "config": self.config,
            "loaded_at": self.loaded_at.isoformat() if self.loaded_at else None,
            "error": self.error,
        }


class Plugin(ABC):
    """
    Base class for all plugins

    Plugins extend RAE functionality by hooking into various lifecycle events.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize plugin

        Args:
            config: Plugin configuration dictionary
        """
        self.config = config or {}
        self.logger = structlog.get_logger(self.__class__.__name__)
        self._metadata: Optional[PluginMetadata] = None

    @property
    def metadata(self) -> PluginMetadata:
        """
        Plugin metadata

        Cached property that ensures the same metadata instance is returned.
        Subclasses should override _create_metadata() to provide their metadata.
        """
        if self._metadata is None:
            self._metadata = self._create_metadata()
        return self._metadata

    @abstractmethod
    def _create_metadata(self) -> PluginMetadata:
        """
        Create plugin metadata

        Must be implemented by subclasses to provide plugin information.
        This is called only once, and the result is cached.
        """
        pass

    async def initialize(self):
        """
        Initialize plugin

        Called when plugin is loaded. Override to perform setup.
        """
        self.logger.info("plugin_initialized", name=self.metadata.name)

    async def shutdown(self):
        """
        Shutdown plugin

        Called when plugin is unloaded. Override to perform cleanup.
        """
        self.logger.info("plugin_shutdown", name=self.metadata.name)

    async def health_check(self) -> Dict[str, Any]:
        """
        Health check for plugin

        Returns:
            Health status dictionary
        """
        return {
            "plugin": self.metadata.name,
            "status": "healthy",
            "enabled": self.metadata.enabled,
        }

    # Hook methods - override to implement functionality

    async def on_before_memory_create(
        self, tenant_id: UUID, memory_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Called before creating a memory

        Can modify memory_data before creation.

        Args:
            tenant_id: Tenant UUID
            memory_data: Memory data to be created

        Returns:
            Modified memory_data
        """
        return memory_data

    @abstractmethod
    async def on_after_memory_create(
        self, tenant_id: UUID, memory_id: str, memory_data: Dict[str, Any]
    ):
        """
        Called after creating a memory

        Args:
            tenant_id: Tenant UUID
            memory_id: Created memory ID
            memory_data: Created memory data
        """
        pass

    async def on_before_memory_update(
        self, tenant_id: UUID, memory_id: str, update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Called before updating a memory

        Args:
            tenant_id: Tenant UUID
            memory_id: Memory ID
            update_data: Update data

        Returns:
            Modified update_data
        """
        return update_data

    @abstractmethod
    async def on_after_memory_update(
        self,
        tenant_id: UUID,
        memory_id: str,
        old_data: Dict[str, Any],
        new_data: Dict[str, Any],
    ):
        """
        Called after updating a memory

        Args:
            tenant_id: Tenant UUID
            memory_id: Memory ID
            old_data: Previous memory data
            new_data: Updated memory data
        """
        pass

    @abstractmethod
    async def on_before_memory_delete(self, tenant_id: UUID, memory_id: str):
        """
        Called before deleting a memory

        Args:
            tenant_id: Tenant UUID
            memory_id: Memory ID to delete
        """
        pass

    @abstractmethod
    async def on_after_memory_delete(self, tenant_id: UUID, memory_id: str):
        """
        Called after deleting a memory

        Args:
            tenant_id: Tenant UUID
            memory_id: Deleted memory ID
        """
        pass

    async def on_before_query(
        self, tenant_id: UUID, query: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Called before executing a query

        Args:
            tenant_id: Tenant UUID
            query: Query string
            params: Query parameters

        Returns:
            Modified params
        """
        return params

    @abstractmethod
    async def on_after_query(
        self, tenant_id: UUID, query: str, results: List[Dict[str, Any]]
    ):
        """
        Called after executing a query

        Args:
            tenant_id: Tenant UUID
            query: Query string
            results: Query results
        """
        pass

    async def on_query_results_transform(
        self, tenant_id: UUID, results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Transform query results

        Args:
            tenant_id: Tenant UUID
            results: Original results

        Returns:
            Transformed results
        """
        return results

    @abstractmethod
    async def on_notification(
        self, tenant_id: UUID, notification_type: str, data: Dict[str, Any]
    ):
        """
        Handle notification event

        Args:
            tenant_id: Tenant UUID
            notification_type: Type of notification
            data: Notification data
        """
        pass

    @abstractmethod
    async def on_alert(
        self,
        tenant_id: UUID,
        alert_type: str,
        severity: str,
        message: str,
        data: Dict[str, Any],
    ):
        """
        Handle alert event

        Args:
            tenant_id: Tenant UUID
            alert_type: Type of alert
            severity: Alert severity (info, warning, error, critical)
            message: Alert message
            data: Additional alert data
        """
        pass


class PluginRegistry:
    """Registry for managing plugins"""

    def __init__(self):
        self._plugins: Dict[str, Plugin] = {}
        self._hooks: Dict[PluginHook, List[Plugin]] = {hook: [] for hook in PluginHook}

    def register(self, plugin: Plugin):
        """
        Register a plugin

        Args:
            plugin: Plugin instance to register
        """
        metadata = plugin.metadata

        if metadata.name in self._plugins:
            logger.warning(
                "plugin_already_registered",
                name=metadata.name,
                message="Overwriting existing plugin",
            )

        self._plugins[metadata.name] = plugin
        metadata.loaded_at = datetime.now(timezone.utc)

        # Register plugin for its hooks
        for hook in metadata.hooks:
            if plugin not in self._hooks[hook]:
                self._hooks[hook].append(plugin)

        logger.info(
            "plugin_registered",
            name=metadata.name,
            version=metadata.version,
            hooks=[h.value for h in metadata.hooks],
        )

    def unregister(self, plugin_name: str):
        """
        Unregister a plugin

        Args:
            plugin_name: Name of plugin to unregister
        """
        if plugin_name not in self._plugins:
            logger.warning("plugin_not_found", name=plugin_name)
            return

        plugin = self._plugins[plugin_name]

        # Remove from hooks
        for hook_plugins in self._hooks.values():
            if plugin in hook_plugins:
                hook_plugins.remove(plugin)

        del self._plugins[plugin_name]

        logger.info("plugin_unregistered", name=plugin_name)

    def get(self, plugin_name: str) -> Optional[Plugin]:
        """Get plugin by name"""
        return self._plugins.get(plugin_name)

    def list_plugins(self) -> List[PluginMetadata]:
        """List all registered plugins"""
        return [plugin.metadata for plugin in self._plugins.values()]

    def get_plugins_for_hook(self, hook: PluginHook) -> List[Plugin]:
        """
        Get all enabled plugins for a specific hook

        Args:
            hook: Plugin hook

        Returns:
            List of plugins that handle this hook
        """
        plugins = self._hooks.get(hook, [])
        return [p for p in plugins if p.metadata.enabled]

    async def initialize_all(self):
        """Initialize all registered plugins"""
        logger.info("initializing_plugins", count=len(self._plugins))

        for plugin in self._plugins.values():
            if plugin.metadata.enabled:
                try:
                    await plugin.initialize()
                except Exception as e:
                    logger.error(
                        "plugin_init_failed", name=plugin.metadata.name, error=str(e)
                    )
                    plugin.metadata.error = str(e)
                    plugin.metadata.enabled = False

    async def shutdown_all(self):
        """Shutdown all plugins"""
        logger.info("shutting_down_plugins", count=len(self._plugins))

        for plugin in self._plugins.values():
            try:
                await plugin.shutdown()
            except Exception as e:
                logger.error(
                    "plugin_shutdown_failed", name=plugin.metadata.name, error=str(e)
                )

    async def execute_hook(self, hook: PluginHook, *args, **kwargs) -> Any:
        """
        Execute a plugin hook

        Args:
            hook: Hook to execute
            *args: Positional arguments for hook
            **kwargs: Keyword arguments for hook

        Returns:
            Result from hook execution (varies by hook type)
        """
        plugins = self.get_plugins_for_hook(hook)

        if not plugins:
            # No plugins for this hook
            return kwargs.get("data") if "data" in kwargs else None

        results = []

        for plugin in plugins:
            try:
                # Get the hook method
                method_name = f"on_{hook.value}"
                method = getattr(plugin, method_name, None)

                if method and callable(method):
                    result = await method(*args, **kwargs)
                    results.append(result)

            except Exception as e:
                logger.error(
                    "plugin_hook_failed",
                    plugin=plugin.metadata.name,
                    hook=hook.value,
                    error=str(e),
                )

        # For transform hooks, chain results
        if hook in [
            PluginHook.BEFORE_MEMORY_CREATE,
            PluginHook.BEFORE_MEMORY_UPDATE,
            PluginHook.BEFORE_QUERY,
            PluginHook.QUERY_RESULTS_TRANSFORM,
        ]:
            # Chain transformations
            data = kwargs.get("data")
            for result in results:
                if result is not None:
                    data = result
            return data

        return results

    def load_plugins_from_directory(self, directory: str):
        """
        Load plugins from a directory

        Args:
            directory: Directory path containing plugin modules
        """
        plugin_dir = Path(directory)

        if not plugin_dir.exists():
            logger.warning("plugin_directory_not_found", directory=directory)
            return

        logger.info("loading_plugins_from_directory", directory=directory)

        for plugin_file in plugin_dir.glob("*.py"):
            if plugin_file.name.startswith("_"):
                continue

            module_name = plugin_file.stem

            try:
                # Import plugin module
                spec = importlib.util.spec_from_file_location(
                    f"plugins.{module_name}", plugin_file
                )
                if spec is not None and spec.loader is not None:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    # Find Plugin classes in module
                    for _name, obj in inspect.getmembers(module):
                        if (
                            inspect.isclass(obj)
                            and issubclass(obj, Plugin)
                            and obj is not Plugin
                        ):
                            # Instantiate and register plugin
                            plugin_instance = obj()
                            self.register(plugin_instance)
                else:
                    logger.warning(
                        "plugin_spec_or_loader_not_found", module=module_name
                    )

            except Exception as e:
                logger.error("plugin_load_failed", module=module_name, error=str(e))

    async def health_check_all(self) -> Dict[str, Any]:
        """
        Run health checks on all plugins

        Returns:
            Health status for all plugins
        """
        results = {}

        for plugin in self._plugins.values():
            try:
                health = await plugin.health_check()
                results[plugin.metadata.name] = health
            except Exception as e:
                results[plugin.metadata.name] = {"status": "unhealthy", "error": str(e)}

        return results


# Global plugin registry instance
_registry = None


def get_plugin_registry() -> PluginRegistry:
    """Get global plugin registry instance"""
    global _registry
    if _registry is None:
        _registry = PluginRegistry()
    return _registry
