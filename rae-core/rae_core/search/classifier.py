"""Rules-first deterministic query classifier for RAE retrieval routing (<0.5ms)."""

from __future__ import annotations

import re
from typing import NamedTuple

from rae_core.evaluation.golden_queries import QueryCategory

# Compiled high-speed regexes
UUID_PATTERN = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
GIT_HASH_PATTERN = re.compile(r"\b[0-9a-f]{7,40}\b")
CVE_PATTERN = re.compile(r"\bCVE-\d{4}-\d{4,7}\b", re.IGNORECASE)
TICKET_PATTERN = re.compile(r"\b[A-Z]{2,10}-\d+\b")

CODE_EXTENSION_PATTERN = re.compile(
    r"\b\w+\.(py|ts|js|go|rs|cpp|c|h|java|json|yaml|yml|md|sql|toml)\b",
    re.IGNORECASE,
)
CAMEL_CASE_PATTERN = re.compile(r"\b[A-Z][a-z0-9]+[A-Z][a-zA-Z0-9]*\b")
METHOD_CALL_PATTERN = re.compile(r"\b[a-zA-Z_][a-zA-Z0-9_]*\s*\(\)")
SNAKE_CASE_PATTERN = re.compile(r"\b[a-z0-9]+_[a-z0-9_]+\b")

GRAPH_RELATION_KEYWORDS = (
    "gdzie jest wywoływany",
    "gdzie jest używany",
    "kto wywołuje",
    "kto dziedziczy",
    "zależy od",
    "relacja między",
    "powiązane z",
    "who calls",
    "where is called",
    "where is used",
    "called by",
    "caller of",
    "callee of",
    "inherits from",
    "depends on",
    "dependency of",
    "implements",
    "subclass of",
    "references to",
    "referenced by",
)

HISTORICAL_KEYWORDS = (
    "dlaczego zmieniono",
    "decyzja architektoniczna",
    "kiedy wprowadzono",
    "historia zmian",
    "poprzednia wersja",
    "adr",
    "why did we change",
    "decision behind",
    "history of",
    "commit when",
    "changelog",
    "previously",
    "regression introduced",
)


class ClassificationResult(NamedTuple):
    category: QueryCategory
    confidence: float
    matched_rule: str


class QueryClassifier:
    """
    Deterministic rules-first query classifier.
    Categorizes incoming search queries in under 0.5ms without external LLM dependencies.
    """

    def classify(self, query: str) -> ClassificationResult:
        query_stripped = query.strip()
        if not query_stripped:
            return ClassificationResult(
                category=QueryCategory.SEMANTIC_CODE,
                confidence=0.5,
                matched_rule="empty_fallback",
            )

        # 1. Exact Identifier checks (Highest priority)
        if UUID_PATTERN.search(query_stripped):
            return ClassificationResult(
                category=QueryCategory.EXACT_IDENTIFIER,
                confidence=1.0,
                matched_rule="uuid_match",
            )
        if CVE_PATTERN.search(query_stripped):
            return ClassificationResult(
                category=QueryCategory.EXACT_IDENTIFIER,
                confidence=1.0,
                matched_rule="cve_pattern",
            )
        if TICKET_PATTERN.search(query_stripped):
            return ClassificationResult(
                category=QueryCategory.EXACT_IDENTIFIER,
                confidence=0.95,
                matched_rule="ticket_pattern",
            )
        # Check git hash only if query consists primarily of hex characters
        words = query_stripped.split()
        for w in words:
            if len(w) in (7, 8, 40) and GIT_HASH_PATTERN.fullmatch(w):
                return ClassificationResult(
                    category=QueryCategory.EXACT_IDENTIFIER,
                    confidence=0.90,
                    matched_rule="git_hash_match",
                )

        # 2. Graph Relation checks
        query_lower = query_stripped.lower()
        if any(phrase in query_lower for phrase in GRAPH_RELATION_KEYWORDS):
            return ClassificationResult(
                category=QueryCategory.GRAPH_RELATION,
                confidence=0.90,
                matched_rule="graph_relation_keywords",
            )

        # 3. Historical Decision checks
        if any(phrase in query_lower for phrase in HISTORICAL_KEYWORDS):
            return ClassificationResult(
                category=QueryCategory.HISTORICAL_DECISION,
                confidence=0.85,
                matched_rule="historical_keywords",
            )

        # 4. Code Symbol checks
        if CODE_EXTENSION_PATTERN.search(query_stripped):
            return ClassificationResult(
                category=QueryCategory.CODE_SYMBOL,
                confidence=0.95,
                matched_rule="file_extension_match",
            )
        if METHOD_CALL_PATTERN.search(query_stripped):
            return ClassificationResult(
                category=QueryCategory.CODE_SYMBOL,
                confidence=0.90,
                matched_rule="method_call_match",
            )
        if CAMEL_CASE_PATTERN.search(query_stripped):
            return ClassificationResult(
                category=QueryCategory.CODE_SYMBOL,
                confidence=0.85,
                matched_rule="camel_case_symbol",
            )
        # Snake_case detection for code tokens
        snake_matches = SNAKE_CASE_PATTERN.findall(query_stripped)
        if snake_matches and len(snake_matches) >= 1:
            return ClassificationResult(
                category=QueryCategory.CODE_SYMBOL,
                confidence=0.80,
                matched_rule="snake_case_symbol",
            )

        # 5. Default Fallback: Semantic Code
        return ClassificationResult(
            category=QueryCategory.SEMANTIC_CODE,
            confidence=0.70,
            matched_rule="default_semantic_fallback",
        )
