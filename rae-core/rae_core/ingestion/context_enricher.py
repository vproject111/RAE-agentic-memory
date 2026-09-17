"""Deterministic Context Enricher for RAE memory ingestion."""

from __future__ import annotations

import ast
import os
import re
from pathlib import Path
from typing import Any

from rae_core.models.envelope import CodeAttribution, ContextEnvelope
from rae_core.models.memory import MemoryItem

EXTENSION_LANGUAGE_MAP: dict[str, str] = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript-react",
    ".js": "javascript",
    ".jsx": "javascript-react",
    ".php": "php",
    ".sql": "sql",
    ".sh": "bash",
    ".bash": "bash",
    ".md": "markdown",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".html": "html",
    ".css": "css",
}


class ContextEnricher:
    """
    Enriches ingested memory items with structural provenance metadata
    without modifying or diluting the raw content.
    """

    def __init__(
        self, default_project: str = "rae_suite", force_enabled: bool | None = None
    ):
        self.default_project = default_project
        self._force_enabled = force_enabled

    @property
    def is_enabled(self) -> bool:
        """Check if context envelope enrichment is enabled via env var or config."""
        if self._force_enabled is not None:
            return self._force_enabled
        env_val = os.getenv("RAE_CONTEXT_ENVELOPE_ENABLED", "false").lower()
        return env_val in ("true", "1", "yes", "on")

    def detect_language(self, file_path: str) -> str | None:
        """Detect language from file extension."""
        suffix = Path(file_path).suffix.lower()
        return EXTENSION_LANGUAGE_MAP.get(suffix)

    def extract_python_symbols(
        self, code: str
    ) -> tuple[str | None, str | None, int | None, int | None, str | None]:
        """
        Extract class name, function name, line bounds, and docstring from Python code via AST.
        Returns: (class_name, function_name, start_line, end_line, summary)
        """
        try:
            tree = ast.parse(code)
        except Exception:
            return None, None, None, None, None

        class_name: str | None = None
        func_name: str | None = None
        start_line: int | None = None
        end_line: int | None = None
        summary: str | None = None

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name
                start_line = getattr(node, "lineno", None)
                end_line = getattr(node, "end_lineno", None)
                doc = ast.get_docstring(node)
                if doc:
                    summary = doc.split("\n")[0].strip()
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not func_name:
                    func_name = node.name
                    if start_line is None:
                        start_line = getattr(node, "lineno", None)
                        end_line = getattr(node, "end_lineno", None)
                    doc = ast.get_docstring(node)
                    if doc and not summary:
                        summary = doc.split("\n")[0].strip()

        return class_name, func_name, start_line, end_line, summary

    def extract_generic_symbols(
        self, code: str, language: str | None
    ) -> tuple[str | None, str | None, int | None, int | None, str | None]:
        """Extract symbols using regex for non-Python languages."""
        class_name: str | None = None
        func_name: str | None = None

        class_match = re.search(r"\b(?:class|interface|trait)\s+([A-Za-z0-9_]+)", code)
        if class_match:
            class_name = class_match.group(1)

        func_match = re.search(
            r"\b(?:function|def|fn|async\s+function)\s+([A-Za-z0-9_]+)", code
        )
        if func_match:
            func_name = func_match.group(1)

        summary = None
        if class_name and func_name:
            summary = f"{class_name}.{func_name}() implementation"
        elif class_name:
            summary = f"Class {class_name} definition"
        elif func_name:
            summary = f"Function {func_name}() definition"

        return class_name, func_name, None, None, summary

    def build_envelope(
        self,
        content: str,
        file_path: str | None = None,
        project: str | None = None,
        repository: str | None = None,
        branch: str | None = None,
        commit_sha: str | None = None,
        task_id: str | None = None,
        trace_id: str | None = None,
        correlation_id: str | None = None,
        source_type: str | None = None,
        scope_tags: list[str] | None = None,
        **kwargs: Any,
    ) -> ContextEnvelope:
        """Construct a ContextEnvelope deterministically."""
        resolved_project = project or self.default_project
        resolved_repo = repository or os.getenv("GIT_REPO", "RAE-Suite")
        resolved_branch = branch or os.getenv("GIT_BRANCH")
        resolved_commit = commit_sha or os.getenv("GIT_COMMIT")

        attribution: CodeAttribution | None = None
        detected_summary: str | None = None

        if file_path:
            lang = self.detect_language(file_path)
            if lang == "python":
                c_name, f_name, s_line, e_line, doc_sum = self.extract_python_symbols(
                    content
                )
            else:
                c_name, f_name, s_line, e_line, doc_sum = self.extract_generic_symbols(
                    content, lang
                )

            attribution = CodeAttribution(
                repository=resolved_repo,
                branch=resolved_branch,
                commit_sha=resolved_commit,
                file_path=file_path,
                language=lang,
                class_name=c_name,
                function_name=f_name,
                start_line=s_line,
                end_line=e_line,
            )
            detected_summary = doc_sum

        # Infer source type if not provided
        resolved_source_type = source_type or ("code" if file_path else "doc")
        if file_path and ("test" in file_path.lower() or "tests/" in file_path.lower()):
            resolved_source_type = "test"

        tags = list(scope_tags or [])
        if attribution and attribution.language:
            tags.append(attribution.language)
        if attribution and attribution.class_name:
            tags.append(attribution.class_name)

        return ContextEnvelope(
            source_type=resolved_source_type,
            project=resolved_project,
            task_id=task_id,
            trace_id=trace_id,
            correlation_id=correlation_id,
            attribution=attribution,
            scope_tags=list(set(tags)),
            semantic_summary=detected_summary,
            metadata=kwargs,
        )

    def enrich_memory_item(
        self,
        memory: MemoryItem,
        file_path: str | None = None,
        project: str | None = None,
        repository: str | None = None,
        branch: str | None = None,
        commit_sha: str | None = None,
        task_id: str | None = None,
        trace_id: str | None = None,
        correlation_id: str | None = None,
        source_type: str | None = None,
        scope_tags: list[str] | None = None,
        **kwargs: Any,
    ) -> MemoryItem:
        """
        Attach ContextEnvelope to MemoryItem if feature flag is active.
        Guarantees ZERO modification to memory.content.
        """
        if not self.is_enabled:
            return memory

        envelope = self.build_envelope(
            content=memory.content,
            file_path=file_path,
            project=project or memory.project or self.default_project,
            repository=repository,
            branch=branch,
            commit_sha=commit_sha,
            task_id=task_id,
            trace_id=trace_id,
            correlation_id=correlation_id,
            source_type=source_type,
            scope_tags=scope_tags,
            **kwargs,
        )
        memory.envelope = envelope
        return memory
