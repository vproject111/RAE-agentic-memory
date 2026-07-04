import re
from unittest.mock import MagicMock, patch

import pytest

# Import the module to access global variables dynamically
from apps.memory_api.observability import pii_scrubber as pii_scrubber_module
from apps.memory_api.observability.pii_scrubber import (
    PII_PATTERNS,
    REDACTION_TOKENS,
    PIIScrubber,
    configure_scrubber,
    detect_pii,
    has_pii,
    scrub_pii,
    scrub_span_attributes,
)


@pytest.fixture(autouse=True)
def reset_global_scrubber():
    """Resets the global _scrubber instance before each test."""
    old_scrubber = pii_scrubber_module._scrubber
    pii_scrubber_module._scrubber = None
    yield
    pii_scrubber_module._scrubber = old_scrubber  # Restore after test if needed


@pytest.fixture
def default_scrubber():
    return PIIScrubber()


def test_pii_scrubber_init_default_patterns(default_scrubber):
    # Adjusted for name_pattern being possibly commented out or present.
    expected_pattern_count = len(PII_PATTERNS) - (
        1 if "name_pattern" not in PII_PATTERNS else 0
    )
    assert len(default_scrubber.patterns) == expected_pattern_count
    assert "email" in default_scrubber.patterns


def test_pii_scrubber_init_enabled_patterns():
    scrubber = PIIScrubber(enabled_patterns=["email", "phone_us"])
    assert "email" in scrubber.patterns
    assert "phone_us" in scrubber.patterns
    assert "ssn" not in scrubber.patterns


def test_pii_scrubber_init_custom_patterns():
    custom_regex = re.compile(r"CUSTOM-\d{3}")
    scrubber = PIIScrubber(custom_patterns={"custom_id": custom_regex})
    assert "custom_id" in scrubber.patterns
    assert scrubber.patterns["custom_id"] == custom_regex


# --- Test scrub method ---


@pytest.mark.parametrize(
    "text, expected, preserve_structure",
    [
        ("test@example.com", REDACTION_TOKENS["email"], False),
        (
            "My email is test@example.com",
            f"My email is {REDACTION_TOKENS['email']}",
            False,
        ),
        (
            "My email is test@example.com",
            "My email is [EMAIL]*********",
            True,
        ),  # "test@example.com" (16) -> "[EMAIL]" (7). Need 9 asterisks.
        ("123-45-6789", REDACTION_TOKENS["ssn"], False),
        (
            "SSN: 123-45-6789",
            "SSN: [SSN]******",
            True,
        ),  # "123-45-6789" (11) -> "[SSN]" (5). Need 6 asterisks.
        ("192.168.1.1", REDACTION_TOKENS["ipv4"], False),
        (
            "My IP is 192.168.1.1",
            "My IP is [IP_ADDRESS",
            True,
        ),  # "192.168.1.1" (11) -> "[IP_ADDRESS]" (12). Truncate to 11 chars.
        ("No PII here.", "No PII here.", False),
        ("", "", False),
        (None, None, False),
    ],
)
def test_scrub_method(default_scrubber, text, expected, preserve_structure):
    if text is None:
        assert default_scrubber.scrub(text, preserve_structure) is None
    else:
        assert default_scrubber.scrub(text, preserve_structure) == expected


# --- Test detect method ---


@pytest.mark.parametrize(
    "text, expected_detections",
    [
        ("test@example.com", {"email": ["test@example.com"]}),
        (
            "Call me at 555-123-4567 or email at user@domain.com",
            {
                "phone_us": ["555-123-4567"],  # Regex updated to return full match
                "email": ["user@domain.com"],
            },
        ),
        ("No PII here.", {}),
        ("", {}),
        (None, {}),
    ],
)
def test_detect_method(default_scrubber, text, expected_detections):
    if text is None:
        assert default_scrubber.detect(text) == {}
    else:
        actual = default_scrubber.detect(text)
        # Convert lists to sets for comparison to ignore order
        assert {k: set(v) for k, v in actual.items()} == {
            k: set(v) for k, v in expected_detections.items()
        }


# --- Test has_pii method ---


@pytest.mark.parametrize(
    "text, expected_result",
    [
        ("test@example.com", True),
        ("No PII here.", False),
        ("", False),
        (None, False),
    ],
)
def test_has_pii_method(default_scrubber, text, expected_result):
    assert default_scrubber.has_pii(text) == expected_result


# --- Test _preserve_length helper ---


@pytest.mark.parametrize(
    "original, replacement, expected",
    [
        ("longtext", "[SHORT]", "[SHORT]*"),  # Original 8, Replacement 7. Need 1 *
        (
            "[LONG_REPLACEMENT]",
            "short",
            "short*************",
        ),  # Original 18, Replacement 5. Need 13 *
        ("exact", "exact", "exact"),
    ],
)
def test_preserve_length(default_scrubber, original, replacement, expected):
    assert default_scrubber._preserve_length(original, replacement) == expected


# --- Test global functions ---


def test_global_scrub_pii(reset_global_scrubber):
    configure_scrubber(enabled_patterns=["email"])
    text = "My email is test@example.com"
    expected = "My email is [EMAIL]*********"  # "test@example.com" (16) -> "[EMAIL]" (7). Need 9 asterisks.
    assert scrub_pii(text, preserve_structure=True) == expected

    configure_scrubber(enabled_patterns=["phone_us"])  # Reconfigure
    text = "Call me at 555-123-4567"
    expected = "Call me at [PHONE]*****"  # "555-123-4567" (12) -> "[PHONE]" (7). Need 5 asterisks.
    assert scrub_pii(text, preserve_structure=True) == expected


def test_global_detect_pii(reset_global_scrubber):
    configure_scrubber(
        enabled_patterns=["email"]
    )  # Ensure scrubber is initialized with email
    text = "My email is test@example.com"
    detected = detect_pii(text)
    assert detected == {"email": ["test@example.com"]}


def test_global_has_pii(reset_global_scrubber):
    configure_scrubber(
        enabled_patterns=["email"]
    )  # Ensure scrubber is initialized with email
    text = "My email is test@example.com"
    assert has_pii(text) is True


def test_global_configure_scrubber(reset_global_scrubber):
    assert pii_scrubber_module._scrubber is None
    configure_scrubber(enabled_patterns=["email"])
    assert pii_scrubber_module._scrubber is not None
    assert "email" in pii_scrubber_module._scrubber.patterns
    assert "phone_us" not in pii_scrubber_module._scrubber.patterns

    # Re-configure with custom patterns only, which should override previous config
    configure_scrubber(
        enabled_patterns=[], custom_patterns={"secret_id": re.compile(r"SECRET-\d{4}")}
    )
    assert "secret_id" in pii_scrubber_module._scrubber.patterns
    assert "email" not in pii_scrubber_module._scrubber.patterns
    assert (
        "phone_us" not in pii_scrubber_module._scrubber.patterns
    )  # Should be clear when enabled_patterns is []


# --- Test scrub_span_attributes ---


@pytest.mark.parametrize(
    "attributes, expected_scrubbed_attributes",
    [
        (
            {"user.email": "test@example.com", "event.id": 123},
            {"user.email": "[EMAIL]*********", "event.id": 123},
        ),
        (
            {"user.emails": ["a@b.com", "c@d.com"], "numbers": [1, 2, 3]},
            {
                "user.emails": ["[EMAIL]", "[EMAIL]"],
                "numbers": [1, 2, 3],
            },  # "a@b.com" (7) -> "[EMAIL]" (7). No padding.
        ),
        (
            {"nested": {"email": "nested@example.com"}},
            {
                "nested": {"email": "[EMAIL]***********"}
            },  # "nested@example.com" (18) -> "[EMAIL]" (7). Need 11 asterisks.
        ),
        ({"no_pii": "safe string"}, {"no_pii": "safe string"}),
        (None, None),
        ({}, {}),
    ],
)
def test_scrub_span_attributes(
    default_scrubber, attributes, expected_scrubbed_attributes
):
    # Ensure global scrubber is configured for this test if it gets used implicitly
    with patch(
        "apps.memory_api.observability.pii_scrubber.get_scrubber",
        return_value=default_scrubber,
    ):
        actual = scrub_span_attributes(attributes)
        assert actual == expected_scrubbed_attributes


def test_create_pii_scrubbing_processor_instantiation_and_on_end():
    # Import the function from the module
    from apps.memory_api.observability.pii_scrubber import (
        create_pii_scrubbing_processor,
    )

    # Mock the get_scrubber to return a real PIIScrubber with default patterns
    with patch(
        "apps.memory_api.observability.pii_scrubber.get_scrubber"
    ) as mock_get_scrubber:
        mock_get_scrubber.return_value = PIIScrubber()

        # Call the function. It might return a real PIIScrubbingProcessor or a DummyProcessor
        # depending on whether opentelemetry is installed.
        processor = create_pii_scrubbing_processor()

        # If opentelemetry is installed, we can test more logic.
        # Even if it returns a DummyProcessor, it should have an on_end method.
        assert hasattr(processor, "on_end")

        # Create a mock span with attributes
        mock_span = MagicMock()
        mock_span.attributes = {"user.email": "test@example.com"}

        # To test the effect, we need to inspect what on_end does.
        # If it modifies span._attributes (as in the real impl), we check that.
        # If it's a dummy, it might do nothing.
        # Let's check if we can force the "real" logic path by mocking sys.modules or similar if needed,
        # but for now let's just verify it runs without error.
        processor.on_end(mock_span)

        # If the real implementation was used and modified _attributes:
        # (Note: The provided create_pii_scrubbing_processor impl sets span._attributes)
        if hasattr(mock_span, "_attributes"):
            # 16 chars -> [EMAIL] (7 chars) -> 9 asterisks
            assert mock_span._attributes == {"user.email": "[EMAIL]*********"}
