"""
Slack Notifier Plugin

Sends notifications to Slack when important events occur.
"""

from typing import Any, Dict, Optional
from uuid import UUID

import aiohttp

from apps.memory_api.plugins.base import Plugin, PluginHook, PluginMetadata


class SlackNotifierPlugin(Plugin):
    """
    Plugin that sends notifications to Slack

    Configuration:
        webhook_url: Slack webhook URL
        channel: Slack channel to post to
        username: Bot username
        icon_emoji: Bot icon emoji
        notify_on_create: Send notification on memory create
        notify_on_reflection: Send notification on reflection
        notify_on_consolidation: Send notification on consolidation
    """

    def _create_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="slack_notifier",
            version="1.0.0",
            author="RAE Team",
            description="Send notifications to Slack for important events",
            hooks=[
                PluginHook.AFTER_MEMORY_CREATE,
                PluginHook.AFTER_REFLECTION,
                PluginHook.AFTER_CONSOLIDATION,
                PluginHook.ALERT,
            ],
            config=self.config,
        )

    async def initialize(self):
        """Validate configuration"""
        await super().initialize()

        self.webhook_url = self.config.get("webhook_url")
        self.channel = self.config.get("channel", "#rae-notifications")
        self.username = self.config.get("username", "RAE Bot")
        self.icon_emoji = self.config.get("icon_emoji", ":robot_face:")

        self.notify_on_create = self.config.get("notify_on_create", False)
        self.notify_on_reflection = self.config.get("notify_on_reflection", True)
        self.notify_on_consolidation = self.config.get("notify_on_consolidation", True)

        if not self.webhook_url:
            self.logger.warning("slack_webhook_not_configured")

    async def on_after_memory_create(
        self, tenant_id: UUID, memory_id: str, memory_data: Dict[str, Any]
    ):
        """Notify on memory creation"""
        if not self.notify_on_create:
            return

        message = (
            f"*New Memory Created*\n"
            f"Tenant: `{tenant_id}`\n"
            f"Memory ID: `{memory_id}`\n"
            f"Layer: `{memory_data.get('layer', 'unknown')}`\n"
            f"Content: _{memory_data.get('content', '')[:100]}..._"
        )

        await self._send_slack_message(message, color="good")

    async def on_after_reflection(
        self, tenant_id: UUID, reflection_id: str, reflection_data: Dict[str, Any]
    ):
        """Notify on reflection generation"""
        if not self.notify_on_reflection:
            return

        insights = reflection_data.get("insights", [])
        quality = reflection_data.get("quality_score", 0.0)

        message = (
            f"*New Reflection Generated*\n"
            f"Tenant: `{tenant_id}`\n"
            f"Quality Score: `{quality:.2f}`\n"
            f"Insights: {len(insights)}\n"
            f"Strategy: `{reflection_data.get('strategy', 'unknown')}`"
        )

        color = "good" if quality > 0.7 else "warning"
        await self._send_slack_message(message, color=color)

    async def on_after_consolidation(
        self, tenant_id: UUID, consolidation_result: Dict[str, Any]
    ):
        """Notify on memory consolidation"""
        if not self.notify_on_consolidation:
            return

        num_memories = len(consolidation_result.get("source_memory_ids", []))
        target_layer = consolidation_result.get("target_layer", "unknown")

        message = (
            f"*Memory Consolidation Complete*\n"
            f"Tenant: `{tenant_id}`\n"
            f"Memories Consolidated: `{num_memories}`\n"
            f"Target Layer: `{target_layer}`\n"
            f"Success: `{consolidation_result.get('success', False)}`"
        )

        color = "good" if consolidation_result.get("success") else "danger"
        await self._send_slack_message(message, color=color)

    async def on_alert(
        self,
        tenant_id: UUID,
        alert_type: str,
        severity: str,
        message: str,
        data: Dict[str, Any],
    ):
        """Send alerts to Slack"""
        color_map = {
            "info": "good",
            "warning": "warning",
            "error": "danger",
            "critical": "danger",
        }

        slack_message = (
            f"*Alert: {alert_type}*\n"
            f"Severity: `{severity.upper()}`\n"
            f"Tenant: `{tenant_id}`\n"
            f"Message: {message}"
        )

        await self._send_slack_message(
            slack_message, color=color_map.get(severity, "warning")
        )

    async def _send_slack_message(self, message: str, color: Optional[str] = None):
        """
        Send message to Slack

        Args:
            message: Message text
            color: Attachment color (good, warning, danger)
        """
        if not self.webhook_url:
            return

        payload = {
            "channel": self.channel,
            "username": self.username,
            "icon_emoji": self.icon_emoji,
            "attachments": [
                {"text": message, "color": color or "good", "mrkdwn_in": ["text"]}
            ],
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as resp:
                    if resp.status != 200:
                        self.logger.error(
                            "slack_send_failed",
                            status=resp.status,
                            response=await resp.text(),
                        )
        except Exception as e:
            self.logger.error("slack_error", error=str(e))

    async def health_check(self) -> Dict[str, Any]:
        """Check if Slack integration is working"""
        status = await super().health_check()

        if not self.webhook_url:
            status["status"] = "degraded"
            status["message"] = "Webhook URL not configured"
        else:
            status["webhook_configured"] = True

        return status
