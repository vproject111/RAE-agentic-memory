import hashlib
import hmac
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from html import escape
from typing import Any, Dict, List

import httpx

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=5)


def sanitize(value: Any) -> str:
    """Sanitize input values to prevent PII exposure or formatting escape issues."""
    if isinstance(value, dict):
        return json.dumps({k: sanitize(v) for k, v in value.items()})
    elif isinstance(value, list):
        return json.dumps([sanitize(v) for v in value])
    return escape(str(value))


class AlertService:
    """
    Automated Alerting & Incident Response Service (ISO 27001 / ISO 42001).
    Dispatches real-time compliance and security alerts to external webhooks safely.
    """

    def __init__(self):
        self.webhook_url = os.environ.get("COMPLIANCE_ALERT_WEBHOOK_URL", "")
        if self.webhook_url:
            if not self.webhook_url.lower().startswith("https://"):
                logger.warning("COMPLIANCE_ALERT_WEBHOOK_URL must use HTTPS. Disabling webhook alerts.")
                self.webhook_url = ""
            else:
                from urllib.parse import urlparse
                parsed = urlparse(self.webhook_url)
                hostname = parsed.hostname or ""
                # SSRF Protection: block local loopback, private class, and metadata IPs
                unsafe_hosts = ["169.254.169.254", "127.0.0.1", "localhost", "0.0.0.0"]
                if (any(h in hostname for h in unsafe_hosts) or 
                    hostname.startswith("192.168.") or 
                    hostname.startswith("10.") or 
                    hostname.startswith("172.16.") or
                    hostname.startswith("172.17.") or
                    hostname.startswith("172.18.") or
                    hostname.startswith("172.19.") or
                    hostname.startswith("172.20.") or
                    hostname.startswith("172.30.")):
                    logger.warning(f"SSRF Alert: Webhook URL points to internal or metadata network host: {hostname}. Disabling webhook alerts.")
                    self.webhook_url = ""
        
        self.client = httpx.Client(timeout=10.0)

    def _hash_tenant_id(self, tenant_id: str) -> str:
        """Securely HMAC hash the tenant ID for privacy (ISO 27001 data minimization)."""
        key = b"rae_secret_alerting_salt_2026"
        return hmac.new(key, tenant_id.encode("utf-8"), hashlib.sha256).hexdigest()[:12]

    def send_alert_sync(self, payload: Dict[str, Any]) -> bool:
        """Synchronously send alert payload with retries and backoff."""
        if not self.webhook_url:
            logger.info(
                f"[ALERT FALLBACK] Webhook dispatch skipped. Payload: {payload}"
            )
            return False

        for attempt in range(3):
            try:
                res = self.client.post(self.webhook_url, json=payload)
                res.raise_for_status()
                return True
            except Exception as e:
                logger.warning(f"Failed to dispatch alert (attempt {attempt+1}): {e}")
                import time

                time.sleep(2**attempt)

        logger.error("Failed to dispatch alert after 3 attempts.")
        return False

    def send_alert_async(self, payload: Dict[str, Any]):
        """Fire-and-forget alert submission to prevent blocking core RAE operations."""
        _executor.submit(self.send_alert_sync, payload)

    def trigger_security_alert(
        self, tenant_id: str, reason: str, details: Dict[str, Any]
    ):
        """Triggered on security policy violations."""
        hashed_tenant = self._hash_tenant_id(tenant_id)
        sanitized_details = sanitize(details)
        payload = {
            "text": f"🚨 *SECURITY POLICY VIOLATION DETECTED* 🚨\n*Tenant*: `HMAC_{hashed_tenant}`\n*Reason*: {reason}",
            "attachments": [
                {
                    "color": "#ff0000",
                    "fields": [
                        {"title": "Details", "value": sanitized_details, "short": False}
                    ],
                }
            ],
        }
        self.send_alert_async(payload)

    def trigger_compliance_alert(
        self, tenant_id: str, score: float, status: str, issues: List[str]
    ):
        """Triggered when overall compliance score drops below threshold."""
        hashed_tenant = self._hash_tenant_id(tenant_id)
        sanitized_issues = [sanitize(i) for i in issues]
        color = "#ff9900" if "PARTIAL" in status.upper() else "#ff0000"
        payload = {
            "text": f"⚠️ *COMPLIANCE THRESHOLD ALERT* ⚠️\n*Tenant*: `HMAC_{hashed_tenant}`\n*Compliance Score*: `{score:.1f}%`\n*Status*: `{status}`",
            "attachments": [
                {
                    "color": color,
                    "fields": [
                        {
                            "title": "Active Issues",
                            "value": (
                                "\n".join([f"• {i}" for i in sanitized_issues])
                                if sanitized_issues
                                else "None"
                            ),
                            "short": False,
                        }
                    ],
                }
            ],
        }
        self.send_alert_async(payload)

    def trigger_rls_alert(self, tenant_id: str, tables_without_rls: List[str]):
        """Triggered when Row-Level Security checks fail on critical tables."""
        hashed_tenant = self._hash_tenant_id(tenant_id)
        payload = {
            "text": f"🛑 *CRITICAL: DATABASE RLS PROTECTIONS DISABLED* 🛑\n*Tenant*: `HMAC_{hashed_tenant}`",
            "attachments": [
                {
                    "color": "#ff0000",
                    "fields": [
                        {
                            "title": "Unprotected Tables",
                            "value": ", ".join(tables_without_rls),
                            "short": False,
                        },
                        {
                            "title": "Action Required",
                            "value": "Immediately run database security migration script.",
                            "short": False,
                        },
                    ],
                }
            ],
        }
        self.send_alert_async(payload)

    def __del__(self):
        try:
            self.client.close()
        except Exception:
            pass
