"""
UI Observer for RAE-Windows (Experimental).
Uses Microsoft UI Automation to scrape content from active windows (LLM chats).

Note: This module only works on Windows.
"""
import time
import logging
import os
import hashlib
from typing import Dict, Any, Optional

# Graceful import for non-Windows dev environments
try:
    if os.name == 'nt':
        import uiautomation as auto
    else:
        auto = None
except ImportError:
    auto = None

from rae_core.types.enums import InformationClass

logger = logging.getLogger(__name__)

class UIObserver:
    """
    Background observer that scans active window content.
    Designed to capture ephemeral LLM conversations.
    """
    def __init__(self, target_keywords: list[str] = None):
        self.enabled = False
        self.last_content_hashes: Dict[str, str] = {}
        self.targets = target_keywords or ["ChatGPT", "Claude", "Gemini", "DeepSeek"]
        
        if not auto:
            logger.warning("UIObserver disabled: 'uiautomation' lib not found or non-Windows OS.")

    def start(self):
        """Enable observation."""
        if auto:
            self.enabled = True
            logger.info("UIObserver STARTED. Watching for: " + ", ".join(self.targets))

    def stop(self):
        """Disable observation."""
        self.enabled = False
        logger.info("UIObserver STOPPED.")

    def scan_active_window(self) -> Optional[Dict[str, Any]]:
        """
        Scans the current foreground window.
        Returns a memory chunk if relevant content is found and changed.
        """
        if not self.enabled or not auto:
            return None

        try:
            window = auto.GetForegroundControl()
            if not window:
                return None

            title = window.Name
            
            # 1. Detection Strategy (Fast title check)
            matched_target = next((t for t in self.targets if t in title), None)
            if not matched_target:
                return None

            # 2. Throttling/Debouncing
            # We don't want to scrape 100 times/sec.
            # Ideally this is called in a loop with sleep(5) by the service.

            # 3. Extraction (Heuristics)
            # Find the main document/content area.
            # Browsers often expose content via 'Document' control type or specific AutomationIDs.
            content = self._extract_browser_content(window)
            
            if not content or len(content) < 50: # Ignore tiny snippets
                return None

            # 4. Diffing (Deduplication)
            # We hash the content to see if it changed significantly.
            # Simple MD5 is fast enough for text.
            current_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
            last_hash = self.last_content_hashes.get(title)

            if current_hash == last_hash:
                return None # No change since last scan

            self.last_content_hashes[title] = current_hash
            logger.info(f"UIObserver detected update in: {title}")

            # 5. Packaging
            return {
                "content": content,
                "metadata": {
                    "source": "ui_observer",
                    "window_title": title,
                    "provider": matched_target,
                    "capture_method": "uiautomation"
                },
                "info_class": InformationClass.RESTRICTED.value, # 🔒 MANDATORY SECURITY
                "tags": ["chat", "llm_capture", "observed", matched_target.lower()]
            }

        except Exception as e:
            # Don't crash the main loop
            logger.debug(f"UI Scan error: {e}")
            return None

    def _extract_browser_content(self, window) -> str:
        """
        Attempt to extract text from a browser window structure.
        """
        # Strategy A: Look for 'Document' control (Chrome/Edge standard)
        doc = window.Control(ControlTypeName="Document")
        if doc.Exists(0, 0): # Non-blocking check
            # Get Value or Name
            # Note: Getting full text can be slow for huge pages.
            # Optimized approach: Get Name (often contains text for accessibility)
            return doc.Name
        
        # Strategy B: Fallback - Get visible text from children (limited depth)
        # This is expensive, use sparingly.
        # For MVP, we stick to Document control or return empty.
        return ""
