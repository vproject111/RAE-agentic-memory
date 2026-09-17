"""Unit tests for ContextEnricher and ContextEnvelope (Iteration 1)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from rae_core.ingestion.context_enricher import ContextEnricher
from rae_core.models.envelope import CodeAttribution, ContextEnvelope
from rae_core.models.memory import MemoryItem
from rae_core.types.enums import MemoryLayer

# ==============================================================================
# SCHEMA INTEGRITY TESTS
# ==============================================================================


def test_code_attribution_schema():
    attr = CodeAttribution(
        repository="RAE-Suite",
        branch="develop",
        commit_sha="abc1234",
        file_path="rae_core/search/engine.py",
        language="python",
        class_name="HybridSearchEngine",
        function_name="search",
        start_line=100,
        end_line=250,
    )
    assert attr.repository == "RAE-Suite"
    assert attr.class_name == "HybridSearchEngine"

    # Extra fields forbidden
    with pytest.raises(ValidationError):
        CodeAttribution(
            repository="RAE-Suite",
            file_path="test.py",
            unknown_property="illegal",  # type: ignore[call-arg]
        )


def test_context_envelope_schema():
    env = ContextEnvelope(
        source_type="code",
        project="rae_suite",
        task_id="task-001",
        trace_id="trace-xyz",
        semantic_summary="Search engine implementation",
    )
    assert env.project == "rae_suite"
    assert env.source_type == "code"

    # Extra fields forbidden
    with pytest.raises(ValidationError):
        ContextEnvelope(
            project="rae_suite",
            forbidden_key="error",  # type: ignore[call-arg]
        )


# ==============================================================================
# ENRICHER BEHAVIOR TESTS
# ==============================================================================


def test_detect_language():
    enricher = ContextEnricher()
    assert enricher.detect_language("engine.py") == "python"
    assert enricher.detect_language("SheetVisualizer.tsx") == "typescript-react"
    assert enricher.detect_language("GeometricalEngine.php") == "php"
    assert enricher.detect_language("script.sh") == "bash"
    assert enricher.detect_language("README.md") == "markdown"
    assert enricher.detect_language("unknown.xyz") is None


def test_extract_python_symbols():
    code = """
class HybridSearchEngine:
    \"\"\"Orchestrates multiple search strategies.\"\"\"

    async def search(self, query: str) -> list:
        return []
"""
    enricher = ContextEnricher()
    c_name, f_name, s_line, e_line, doc_sum = enricher.extract_python_symbols(code)
    assert c_name == "HybridSearchEngine"
    assert f_name == "search"
    assert s_line is not None
    assert doc_sum == "Orchestrates multiple search strategies."


def test_extract_python_symbols_syntax_error():
    invalid_code = "def broken_code(: invalid syntax !!!"
    enricher = ContextEnricher()
    c_name, f_name, s_line, e_line, doc_sum = enricher.extract_python_symbols(
        invalid_code
    )
    assert c_name is None
    assert f_name is None


def test_extract_generic_symbols():
    enricher = ContextEnricher()

    # TypeScript
    ts_code = (
        "class VisualizerComponent extends React.Component { function render() {} }"
    )
    c_name, f_name, _, _, summary = enricher.extract_generic_symbols(
        ts_code, "typescript"
    )
    assert c_name == "VisualizerComponent"
    assert f_name == "render"
    assert summary is not None

    # PHP
    php_code = "class CalculateAdapter { function calculatePrice() {} }"
    c_name, f_name, _, _, summary = enricher.extract_generic_symbols(php_code, "php")
    assert c_name == "CalculateAdapter"
    assert f_name == "calculatePrice"


def test_build_envelope():
    enricher = ContextEnricher(default_project="rae_core")
    content = "class EmeraldReranker:\n    pass"

    envelope = enricher.build_envelope(
        content=content,
        file_path="rae_core/search/engine.py",
        project="rae_suite",
        repository="RAE-Suite",
        branch="feature/iter1",
        commit_sha="c1a6cdeb",
        task_id="task-123",
        trace_id="trace-456",
    )

    assert isinstance(envelope, ContextEnvelope)
    assert envelope.project == "rae_suite"
    assert envelope.task_id == "task-123"
    assert envelope.attribution is not None
    assert envelope.attribution.class_name == "EmeraldReranker"
    assert envelope.attribution.language == "python"
    assert "python" in envelope.scope_tags
    assert "EmeraldReranker" in envelope.scope_tags


def test_enrich_memory_item_feature_flag_disabled():
    enricher = ContextEnricher(force_enabled=False)
    raw_content = "def test_func(): pass"

    memory = MemoryItem(
        content=raw_content,
        layer=MemoryLayer.WORKING,
        tenant_id="tenant-123",
        agent_id="agent-001",
    )

    result = enricher.enrich_memory_item(memory, file_path="test.py")
    assert result.envelope is None
    assert result.content == raw_content  # Raw content preserved 100%


def test_enrich_memory_item_feature_flag_enabled():
    enricher = ContextEnricher(force_enabled=True)
    raw_content = "class DecisionEngine:\n    def evaluate(self): pass"

    memory = MemoryItem(
        content=raw_content,
        layer=MemoryLayer.SEMANTIC,
        tenant_id="tenant-123",
        agent_id="agent-001",
        project="dreamsoft",
    )

    result = enricher.enrich_memory_item(
        memory=memory,
        file_path="dreamsoft/engine.py",
        repository="dreamsoft_factory",
        branch="develop",
        commit_sha="fedcba98",
        task_id="T-99",
    )

    # Envelope populated
    assert result.envelope is not None
    assert result.envelope.project == "dreamsoft"
    assert result.envelope.attribution is not None
    assert result.envelope.attribution.class_name == "DecisionEngine"
    assert result.envelope.attribution.commit_sha == "fedcba98"

    # Strict invariant: content MUST NOT be changed or diluted
    assert result.content == raw_content
