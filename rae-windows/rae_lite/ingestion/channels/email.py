"""
Email Connector for RAE-Lite.

Handles ingestion of emails from:
1. IMAP (Real-world) - Stub/Structure provided.
2. EML Files (Demo/Local) - Fully implemented for offline demo.
3. Mbox (Archive) - Future.

Crucially, marks content as RESTRICTED (ISO 27000) for safe Idea Extraction.
"""

import email
import logging
from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import Any, Dict, Generator, List

from rae_core.types.enums import InformationClass

logger = logging.getLogger(__name__)

class EmailConnector:
    """
    Standardizes email ingestion.
    """
    
    def parse_eml(self, file_path: Path) -> Dict[str, Any] | None:
        """
        Parse a raw .eml file into a RAE-compatible structure.
        """
        try:
            with open(file_path, 'rb') as fp:
                msg = BytesParser(policy=policy.default).parse(fp)

            # Extract body
            body = msg.get_body(preferencelist=('plain', 'html'))
            content = body.get_content() if body else ""

            # Extract metadata
            metadata = {
                "subject": msg.get("subject", "No Subject"),
                "from": msg.get("from", "Unknown"),
                "to": msg.get("to", "Unknown"),
                "date": msg.get("date", ""),
                "message_id": msg.get("message-id", str(file_path.name)),
                "source_type": "email",
                "source_path": str(file_path)
            }
            
            return {
                "content": content,
                "metadata": metadata,
                "info_class": InformationClass.RESTRICTED.value, # 🔒 CRITICAL: Default to restricted
                "tags": ["email", "communication", "restricted"]
            }

        except Exception as e:
            logger.error(f"Error parsing EML {file_path}: {e}")
            return None

    def process_directory(self, inbox_path: Path) -> Generator[Dict[str, Any], None, None]:
        """
        Scan a directory for .eml files (simulating an inbox).
        """
        if not inbox_path.exists():
            return

        for eml_file in inbox_path.glob("*.eml"):
            result = self.parse_eml(eml_file)
            if result:
                yield result

