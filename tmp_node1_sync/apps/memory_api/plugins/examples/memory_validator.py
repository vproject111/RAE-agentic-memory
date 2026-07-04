"""
Memory Validator Plugin

Validates and enriches memories before creation.
"""

import re
from typing import Any, Dict
from uuid import UUID

from apps.memory_api.plugins.base import Plugin, PluginHook, PluginMetadata


class MemoryValidatorPlugin(Plugin):
    """
    Plugin that validates and enriches memories

    Configuration:
        min_content_length: Minimum content length
        max_content_length: Maximum content length
        required_fields: List of required fields
        auto_tag: Automatically add tags based on content
        detect_language: Detect content language
        profanity_filter: Enable profanity filtering
    """

    def _create_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="memory_validator",
            version="1.0.0",
            author="RAE Team",
            description="Validate and enrich memories before creation",
            hooks=[PluginHook.BEFORE_MEMORY_CREATE, PluginHook.BEFORE_MEMORY_UPDATE],
            config=self.config,
        )

    async def initialize(self):
        """Initialize validator configuration"""
        await super().initialize()

        self.min_content_length = self.config.get("min_content_length", 10)
        self.max_content_length = self.config.get("max_content_length", 50000)
        self.required_fields = self.config.get("required_fields", ["content", "layer"])
        self.auto_tag = self.config.get("auto_tag", True)
        self.detect_language = self.config.get("detect_language", False)
        self.profanity_filter = self.config.get("profanity_filter", False)

        # Common profanity words (very basic example)
        self.profanity_words = set(["spam", "badword"])  # Expand as needed

    async def on_before_memory_create(
        self, tenant_id: UUID, memory_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate and enrich memory before creation

        Args:
            tenant_id: Tenant UUID
            memory_data: Memory data to validate

        Returns:
            Validated and enriched memory data

        Raises:
            ValueError: If validation fails
        """
        # Check required fields
        for field in self.required_fields:
            if field not in memory_data or not memory_data[field]:
                raise ValueError(f"Required field missing: {field}")

        content = memory_data.get("content", "")

        # Validate content length
        if len(content) < self.min_content_length:
            raise ValueError(
                f"Content too short (min: {self.min_content_length} chars)"
            )

        if len(content) > self.max_content_length:
            raise ValueError(f"Content too long (max: {self.max_content_length} chars)")

        # Profanity filter
        if self.profanity_filter:
            memory_data = await self._filter_profanity(memory_data)

        # Auto-tagging
        if self.auto_tag:
            memory_data = await self._auto_tag(memory_data)

        # Language detection
        if self.detect_language:
            memory_data = await self._detect_language(memory_data)

        # Add validation metadata
        if "metadata" not in memory_data:
            memory_data["metadata"] = {}

        memory_data["metadata"]["validated"] = True
        memory_data["metadata"]["validator_version"] = self.metadata.version

        self.logger.info(
            "memory_validated", tenant_id=str(tenant_id), content_length=len(content)
        )

        return memory_data

    async def on_before_memory_update(
        self, tenant_id: UUID, memory_id: str, update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate memory updates

        Args:
            tenant_id: Tenant UUID
            memory_id: Memory ID
            update_data: Update data

        Returns:
            Validated update data
        """
        # Validate content if being updated
        if "content" in update_data:
            content = update_data["content"]

            if len(content) < self.min_content_length:
                raise ValueError(
                    f"Content too short (min: {self.min_content_length} chars)"
                )

            if len(content) > self.max_content_length:
                raise ValueError(
                    f"Content too long (max: {self.max_content_length} chars)"
                )

            # Profanity filter
            if self.profanity_filter:
                update_data = await self._filter_profanity(update_data)

        return update_data

    async def _filter_profanity(self, memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filter profanity from content

        Args:
            memory_data: Memory data

        Returns:
            Filtered memory data
        """
        content = memory_data.get("content", "")

        # Simple word-based filtering
        for word in self.profanity_words:
            if word.lower() in content.lower():
                # Replace with asterisks
                pattern = re.compile(re.escape(word), re.IGNORECASE)
                content = pattern.sub("*" * len(word), content)

        memory_data["content"] = content

        return memory_data

    async def _auto_tag(self, memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Automatically add tags based on content

        Args:
            memory_data: Memory data

        Returns:
            Memory data with auto-generated tags
        """
        content = memory_data.get("content", "").lower()

        # Simple keyword-based tagging
        tag_keywords = {
            "code": ["code", "function", "class", "import", "def", "async"],
            "bug": ["bug", "error", "issue", "problem", "fix"],
            "feature": ["feature", "enhancement", "improvement", "new"],
            "documentation": ["doc", "documentation", "readme", "guide"],
            "api": ["api", "endpoint", "request", "response"],
            "database": ["database", "sql", "query", "table", "schema"],
            "security": ["security", "auth", "permission", "vulnerability"],
            "performance": ["performance", "optimization", "speed", "latency"],
        }

        existing_tags = set(memory_data.get("tags", []))

        for tag, keywords in tag_keywords.items():
            if any(keyword in content for keyword in keywords):
                existing_tags.add(tag)

        memory_data["tags"] = list(existing_tags)

        return memory_data

    async def _detect_language(self, memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect content language

        Args:
            memory_data: Memory data

        Returns:
            Memory data with detected language
        """
        content = memory_data.get("content", "")

        # Very simple language detection (production should use proper library)
        # Check for common words in different languages
        if any(word in content.lower() for word in ["the", "is", "and", "in", "to"]):
            detected_lang = "en"
        elif any(
            word in content.lower() for word in ["der", "die", "das", "und", "ist"]
        ):
            detected_lang = "de"
        elif any(word in content.lower() for word in ["le", "la", "les", "et", "est"]):
            detected_lang = "fr"
        else:
            detected_lang = "unknown"

        if "metadata" not in memory_data:
            memory_data["metadata"] = {}

        memory_data["metadata"]["detected_language"] = detected_lang

        return memory_data

    async def health_check(self) -> Dict[str, Any]:
        """Health check"""
        status = await super().health_check()

        status["configuration"] = {
            "min_content_length": self.min_content_length,
            "max_content_length": self.max_content_length,
            "auto_tag": self.auto_tag,
            "profanity_filter": self.profanity_filter,
        }

        return status
