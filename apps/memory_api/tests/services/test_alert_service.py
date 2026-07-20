import os
from unittest.mock import patch

from apps.memory_api.services.alert_service import AlertService, sanitize


def test_payload_sanitization():
    # Test simple types
    assert sanitize("normal-text") == "normal-text"
    # Test html characters escaping
    assert (
        sanitize("<script>alert(1)</script>") == "&lt;script&gt;alert(1)&lt;/script&gt;"
    )
    # Test nested dictionary sanitization
    details = {"api_key": "sk-12345", "nested": {"nested_key": "<unsafe>"}}
    sanitized = sanitize(details)
    assert "sk-12345" in sanitized
    assert "&lt;unsafe&gt;" in sanitized


def test_alert_service_initialization():
    with patch.dict(
        os.environ,
        {"COMPLIANCE_ALERT_WEBHOOK_URL": "https://hooks.slack.com/services/test"},
    ):
        service = AlertService()
        assert service.webhook_url == "https://hooks.slack.com/services/test"


def test_alert_service_enforces_https():
    with patch.dict(
        os.environ, {"COMPLIANCE_ALERT_WEBHOOK_URL": "http://unsafe.webhook.com"}
    ):
        service = AlertService()
        assert service.webhook_url == ""


def test_alert_service_hmac_hashing():
    service = AlertService()
    tenant_id = "f51d8b92-2fb1-524c-86e4-c6f8f6f59872"
    hash1 = service._hash_tenant_id(tenant_id)
    hash2 = service._hash_tenant_id(tenant_id)
    assert len(hash1) == 12
    assert hash1 == hash2  # Deterministic hmac
    assert hash1 != tenant_id  # Not raw uuid


@patch("apps.memory_api.services.alert_service.AlertService.send_alert_async")
def test_trigger_security_alert(mock_send_async):
    service = AlertService()
    service.trigger_security_alert(
        tenant_id="test-tenant",
        reason="Banned dependency imported",
        details={"library": "sentence-transformers"},
    )
    mock_send_async.assert_called_once()
    payload = mock_send_async.call_args[0][0]
    assert "SECURITY POLICY VIOLATION DETECTED" in payload["text"]
    assert "Banned dependency" in payload["text"]


@patch("apps.memory_api.services.alert_service.AlertService.send_alert_async")
def test_trigger_compliance_alert(mock_send_async):
    service = AlertService()
    service.trigger_compliance_alert(
        tenant_id="test-tenant",
        score=75.4,
        status="PARTIAL_COMPLIANCE",
        issues=["Missing database RLS"],
    )
    mock_send_async.assert_called_once()
    payload = mock_send_async.call_args[0][0]
    assert "COMPLIANCE THRESHOLD ALERT" in payload["text"]
    assert "75.4%" in payload["text"]


@patch("apps.memory_api.services.alert_service.AlertService.send_alert_async")
def test_trigger_rls_alert(mock_send_async):
    service = AlertService()
    service.trigger_rls_alert(
        tenant_id="test-tenant", tables_without_rls=["memories", "budgets"]
    )
    mock_send_async.assert_called_once()
    payload = mock_send_async.call_args[0][0]
    assert "DATABASE RLS PROTECTIONS DISABLED" in payload["text"]
    assert "memories, budgets" in payload["attachments"][0]["fields"][0]["value"]
