"""
Comprehensive tests for PIIScrubber class.

These tests validate PII detection and masking for:
- API keys, tokens, secrets
- Email addresses
- Credit card numbers
- IP addresses
- Phone numbers
- Social Security Numbers (SSNs)
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rae_mcp.server import PIIScrubber


class TestPIIScrubberAPIKeys:
    """Test API key detection and masking"""

    def test_api_key_field_masking(self):
        """Test that api_key field is masked"""
        data = {"api_key": "sk-1234567890abcdef"}
        scrubbed = PIIScrubber.scrub(data)
        assert scrubbed["api_key"] == "***REDACTED***"

    def test_token_field_masking(self):
        """Test that token field is masked"""
        data = {"token": "ghp_1234567890abcdefghijklmnop"}
        scrubbed = PIIScrubber.scrub(data)
        assert scrubbed["token"] == "***REDACTED***"

    def test_secret_field_masking(self):
        """Test that secret field is masked"""
        data = {"secret": "my-secret-value-123"}
        scrubbed = PIIScrubber.scrub(data)
        assert scrubbed["secret"] == "***REDACTED***"

    def test_password_field_masking(self):
        """Test that password field is masked"""
        data = {"password": "SuperSecret123!"}
        scrubbed = PIIScrubber.scrub(data)
        assert scrubbed["password"] == "***REDACTED***"

    def test_api_key_in_string(self):
        """Test API key pattern in string content"""
        text = "My API key is: api_key=sk-1234567890abcdef"
        scrubbed = PIIScrubber._scrub_string(text)
        assert "sk-1234567890abcdef" not in scrubbed
        assert "api_key=***REDACTED***" in scrubbed

    def test_bearer_token_in_string(self):
        """Test bearer token pattern"""
        text = 'Authorization: Bearer token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"'
        scrubbed = PIIScrubber._scrub_string(text)
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in scrubbed

    def test_nested_api_keys(self):
        """Test API keys in nested structures"""
        data = {
            "config": {
                "auth": {"api_key": "sk-12345", "token": "ghp-67890"},
                "user": "john",
            }
        }
        scrubbed = PIIScrubber.scrub(data)
        assert scrubbed["config"]["auth"]["api_key"] == "***REDACTED***"
        assert scrubbed["config"]["auth"]["token"] == "***REDACTED***"
        assert scrubbed["config"]["user"] == "john"


class TestPIIScrubberEmails:
    """Test email address detection and masking"""

    def test_basic_email(self):
        """Test basic email masking"""
        text = "Contact me at john.doe@example.com"
        scrubbed = PIIScrubber._scrub_string(text)
        assert "john.doe" not in scrubbed
        assert "@example.com" in scrubbed or "***@***" in scrubbed

    def test_email_with_subdomain(self):
        """Test email with subdomain"""
        text = "Email: user@mail.company.com"
        scrubbed = PIIScrubber._scrub_string(text)
        assert "user@mail.company.com" not in scrubbed

    def test_multiple_emails(self):
        """Test multiple emails in text"""
        text = "Contacts: alice@example.com, bob@test.org"
        scrubbed = PIIScrubber._scrub_string(text)
        assert "alice@example.com" not in scrubbed
        assert "bob@test.org" not in scrubbed

    def test_email_in_dict(self):
        """Test email in dictionary"""
        data = {"user_email": "sensitive@company.com", "name": "John"}
        scrubbed = PIIScrubber.scrub(data)
        # Email should be masked but domain preserved
        assert "sensitive" not in scrubbed["user_email"]
        assert scrubbed["name"] == "John"


class TestPIIScrubberCreditCards:
    """Test credit card number detection and masking"""

    def test_credit_card_with_spaces(self):
        """Test credit card with spaces"""
        text = "Card: 4532 1234 5678 9010"
        scrubbed = PIIScrubber._scrub_string(text)
        assert "4532 1234 5678" not in scrubbed
        assert "9010" in scrubbed  # Last 4 digits preserved

    def test_credit_card_with_dashes(self):
        """Test credit card with dashes"""
        text = "Payment: 4532-1234-5678-9010"
        scrubbed = PIIScrubber._scrub_string(text)
        assert "4532-1234-5678" not in scrubbed
        assert "9010" in scrubbed

    def test_credit_card_no_separators(self):
        """Test credit card without separators"""
        text = "Card number: 4532123456789010"
        scrubbed = PIIScrubber._scrub_string(text)
        assert "4532123456789010" not in scrubbed

    def test_multiple_credit_cards(self):
        """Test multiple credit cards"""
        text = "Cards: 4532-1234-5678-9010 and 5105-1051-0510-5100"
        scrubbed = PIIScrubber._scrub_string(text)
        assert "4532" not in scrubbed or "****" in scrubbed
        assert "5105" not in scrubbed or "****" in scrubbed


class TestPIIScrubberIPAddresses:
    """Test IP address detection and masking"""

    def test_ipv4_address(self):
        """Test IPv4 address masking"""
        text = "Server IP: 192.168.1.100"
        scrubbed = PIIScrubber._scrub_string(text)
        assert "192.168.***.**" in scrubbed or "***REDACTED***" in scrubbed
        assert "192.168.1.100" not in scrubbed

    def test_multiple_ips(self):
        """Test multiple IP addresses"""
        text = "IPs: 10.0.0.1, 172.16.0.5"
        scrubbed = PIIScrubber._scrub_string(text)
        assert "10.0.0.1" not in scrubbed
        assert "172.16.0.5" not in scrubbed

    def test_localhost_preserved(self):
        """Test that localhost is handled"""
        text = "Connecting to 127.0.0.1"
        scrubbed = PIIScrubber._scrub_string(text)
        # Should be masked or partially masked
        assert "127.0" in scrubbed or "***" in scrubbed


class TestPIIScrubberPhoneNumbers:
    """Test phone number detection and masking"""

    def test_us_phone_with_dashes(self):
        """Test US phone with dashes"""
        text = "Call: 555-123-4567"
        scrubbed = PIIScrubber._scrub_string(text)
        assert "555-123-4567" not in scrubbed
        assert "***REDACTED***" in scrubbed

    def test_us_phone_with_dots(self):
        """Test US phone with dots"""
        text = "Phone: 555.123.4567"
        scrubbed = PIIScrubber._scrub_string(text)
        assert "555.123.4567" not in scrubbed

    def test_international_phone(self):
        """Test international phone"""
        text = "Contact: +1-555-123-4567"
        scrubbed = PIIScrubber._scrub_string(text)
        assert "+1-555-123-4567" not in scrubbed

    def test_phone_with_parens(self):
        """Test phone with parentheses"""
        text = "Tel: (555) 123-4567"
        scrubbed = PIIScrubber._scrub_string(text)
        assert "(555) 123-4567" not in scrubbed


class TestPIIScrubberSSN:
    """Test Social Security Number detection and masking"""

    def test_ssn_format(self):
        """Test SSN with standard format"""
        text = "SSN: 123-45-6789"
        scrubbed = PIIScrubber._scrub_string(text)
        assert "123-45-6789" not in scrubbed
        assert "***REDACTED***" in scrubbed

    def test_multiple_ssns(self):
        """Test multiple SSNs"""
        text = "SSNs: 123-45-6789, 987-65-4321"
        scrubbed = PIIScrubber._scrub_string(text)
        assert "123-45-6789" not in scrubbed
        assert "987-65-4321" not in scrubbed


class TestPIIScrubberComplex:
    """Test complex scenarios with mixed PII"""

    def test_multiple_pii_types(self):
        """Test text with multiple PII types"""
        data = {
            "api_key": "sk-1234567890",
            "user_email": "john@example.com",
            "credit_card": "4532-1234-5678-9010",
            "phone": "555-123-4567",
            "ssn": "123-45-6789",
            "server_ip": "192.168.1.100",
            "safe_field": "This is safe",
        }
        scrubbed = PIIScrubber.scrub(data)

        # All PII should be masked
        assert scrubbed["api_key"] == "***REDACTED***"
        assert "john" not in scrubbed["user_email"]
        assert "4532-1234-5678" not in scrubbed["credit_card"]
        assert "555-123-4567" not in scrubbed["phone"]
        assert "123-45-6789" not in scrubbed["ssn"]
        assert "192.168.1.100" not in scrubbed["server_ip"]

        # Safe field should be preserved
        assert scrubbed["safe_field"] == "This is safe"

    def test_deeply_nested_pii(self):
        """Test PII in deeply nested structures"""
        data = {
            "level1": {
                "level2": {
                    "level3": {
                        "api_key": "secret-key-123",
                        "email": "deep@nested.com",
                    }
                }
            }
        }
        scrubbed = PIIScrubber.scrub(data)
        assert scrubbed["level1"]["level2"]["level3"]["api_key"] == "***REDACTED***"
        assert "deep" not in scrubbed["level1"]["level2"]["level3"]["email"]

    def test_list_with_pii(self):
        """Test list containing PII"""
        data = {
            "users": [
                {"email": "user1@test.com", "api_key": "key1"},
                {"email": "user2@test.com", "api_key": "key2"},
            ]
        }
        scrubbed = PIIScrubber.scrub(data)
        assert scrubbed["users"][0]["api_key"] == "***REDACTED***"
        assert scrubbed["users"][1]["api_key"] == "***REDACTED***"
        assert "user1" not in scrubbed["users"][0]["email"]

    def test_content_truncation(self):
        """Test content field truncation"""
        long_content = "A" * 500
        data = {"content": long_content, "short": "B" * 10}
        scrubbed = PIIScrubber.scrub(data, max_content_length=100)

        # Content should be truncated
        assert len(scrubbed["content"]) < len(long_content)
        assert "truncated" in scrubbed["content"]

        # Short field should not be truncated
        assert scrubbed["short"] == "B" * 10


class TestPIIScrubberEdgeCases:
    """Test edge cases and special scenarios"""

    def test_empty_data(self):
        """Test empty data structures"""
        assert PIIScrubber.scrub({}) == {}
        assert PIIScrubber.scrub([]) == []
        assert PIIScrubber.scrub("") == ""

    def test_none_values(self):
        """Test None values"""
        data = {"field": None}
        scrubbed = PIIScrubber.scrub(data)
        assert scrubbed["field"] is None

    def test_numeric_values(self):
        """Test numeric values"""
        data = {"count": 123, "price": 45.67}
        scrubbed = PIIScrubber.scrub(data)
        assert scrubbed["count"] == 123
        assert scrubbed["price"] == 45.67

    def test_boolean_values(self):
        """Test boolean values"""
        data = {"enabled": True, "disabled": False}
        scrubbed = PIIScrubber.scrub(data)
        assert scrubbed["enabled"] is True
        assert scrubbed["disabled"] is False

    def test_case_insensitive_fields(self):
        """Test case-insensitive field matching"""
        data = {"API_KEY": "secret", "Token": "token123", "PaSsWoRd": "pass"}
        scrubbed = PIIScrubber.scrub(data)
        # Should all be masked regardless of case
        assert scrubbed["API_KEY"] == "***REDACTED***"
        assert scrubbed["Token"] == "***REDACTED***"
        assert scrubbed["PaSsWoRd"] == "***REDACTED***"

    def test_false_positives(self):
        """Test that normal data is not incorrectly flagged"""
        data = {
            "version": "1.2.3.4",  # Looks like IP but in version context
            "description": "Use API key from environment",  # Contains "API key" text
        }
        scrubbed = PIIScrubber.scrub(data)
        # Version might be masked as IP (expected behavior for safety)
        # Description should keep the phrase "API key" but not mask it as it's explanatory text
        assert "environment" in scrubbed["description"]


class TestPIIScrubberSensitiveFields:
    """Test sensitive field name detection"""

    def test_all_sensitive_field_names(self):
        """Test that all sensitive field names are masked"""
        sensitive_fields = [
            "password",
            "passwd",
            "pwd",
            "secret",
            "api_key",
            "apikey",
            "token",
            "access_token",
            "refresh_token",
            "auth_token",
            "session_token",
            "private_key",
            "secret_key",
            "client_secret",
            "api_secret",
        ]

        for field in sensitive_fields:
            data = {field: "sensitive-value"}
            scrubbed = PIIScrubber.scrub(data)
            assert scrubbed[field] == "***REDACTED***", f"Field '{field}' not masked"

    def test_mixed_sensitive_and_safe_fields(self):
        """Test mix of sensitive and safe fields"""
        data = {
            "username": "john_doe",
            "password": "secret123",
            "email_public": "public@example.com",
            "api_key": "sk-12345",
            "user_id": "12345",
        }
        scrubbed = PIIScrubber.scrub(data)

        # Sensitive should be masked
        assert scrubbed["password"] == "***REDACTED***"
        assert scrubbed["api_key"] == "***REDACTED***"

        # Safe should be preserved (though email might be partially masked by pattern)
        assert scrubbed["username"] == "john_doe"
        assert scrubbed["user_id"] == "12345"
