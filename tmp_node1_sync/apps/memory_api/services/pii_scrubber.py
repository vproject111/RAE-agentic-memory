from typing import TYPE_CHECKING, Any, Optional, cast

# Optional ML dependencies
try:  # pragma: no cover
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine
    from presidio_anonymizer.entities import OperatorConfig

    PRESIDIO_AVAILABLE = True
except ImportError:  # pragma: no cover
    AnalyzerEngine = None  # type: ignore[assignment,misc]
    AnonymizerEngine = None  # type: ignore[assignment,misc]
    OperatorConfig = None  # type: ignore[assignment,misc]
    PRESIDIO_AVAILABLE = False

if TYPE_CHECKING:
    from presidio_analyzer import AnalyzerEngine  # noqa: F401
    from presidio_anonymizer import AnonymizerEngine  # noqa: F401
    from presidio_anonymizer.entities import OperatorConfig  # noqa: F401

# Lazy-initialized engines (created on first use)
# These are heavy objects, so we initialize them only when needed
_analyzer: Optional["AnalyzerEngine"] = None
_anonymizer: Optional["AnonymizerEngine"] = None


def _ensure_presidio_available() -> None:
    """Ensure presidio libraries are available."""
    if not PRESIDIO_AVAILABLE:
        raise RuntimeError(
            "PII scrubbing requires presidio-analyzer and presidio-anonymizer. "
            "Install ML extras or run: "
            "`pip install presidio-analyzer presidio-anonymizer`."
        )


def _get_analyzer() -> "AnalyzerEngine":
    """Get or create the analyzer engine (lazy initialization)."""
    global _analyzer
    _ensure_presidio_available()

    if _analyzer is None:
        _analyzer = AnalyzerEngine()  # type: ignore[misc]

    return _analyzer


def _get_anonymizer() -> "AnonymizerEngine":
    """Get or create the anonymizer engine (lazy initialization)."""
    global _anonymizer
    _ensure_presidio_available()

    if _anonymizer is None:
        _anonymizer = AnonymizerEngine()  # type: ignore[misc]

    return _anonymizer


def scrub_text(text: str | None) -> str:
    """
    Analyzes and anonymizes PII in the given text using Presidio.

    If Presidio is not available, returns the original text.

    Args:
        text: The text to scrub for PII

    Returns:
        The text with PII replaced by <PII>, or original text if Presidio is unavailable
    """
    if not text:
        return ""

    if not PRESIDIO_AVAILABLE:
        # Fallback if libraries are not installed
        return text

    # Get engines (lazy initialization)
    analyzer = _get_analyzer()
    anonymizer = _get_anonymizer()

    # Analyze the text for PII entities
    analyzer_results = analyzer.analyze(text=text, language="en")

    # Anonymize the detected entities
    anonymized_text = anonymizer.anonymize(
        text=text,
        analyzer_results=cast(Any, analyzer_results),
        operators={"DEFAULT": OperatorConfig("replace", {"new_value": "<PII>"})},  # type: ignore[misc]
    )

    return cast(str, anonymized_text.text)
