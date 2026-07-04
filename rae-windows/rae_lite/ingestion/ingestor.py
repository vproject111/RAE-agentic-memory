# Universal File Ingestor for RAE-Lite.
# Handles parsing of various file formats (PDF, DOCX, ODT, TXT, MD)
# and converting them into RAE Memory Items.

import os
import time
import logging
import mimetypes
from pathlib import Path
from typing import Any, Generator, Dict, List, Optional
from datetime import datetime, timezone

# Optional imports with graceful fallback
try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    import docx
except ImportError:
    docx = None

try:
    from odf.opendocument import load as load_odt
    from odf.text import P
except ImportError:
    load_odt = None

logger = logging.getLogger(__name__)

class UniversalIngestor:
    """
    Parses files from the filesystem and yields structured chunks
    ready for RAE memory storage.
    """

    SUPPORTED_EXTENSIONS = {
        ".pdf": "pdf",
        ".docx": "docx",
        ".doc": "doc", 
        ".odt": "odt",
        ".txt": "text",
        ".md": "markdown",
        ".py": "code",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".log": "log",
        ".csv": "csv"
    }

    def __init__(self, chunk_size: int = 1000, overlap: int = 100):
        self.chunk_size = chunk_size
        self.overlap = overlap
        
        self._parsers_status = {
            "pdf": fitz is not None,
            "docx": docx is not None,
            "odt": load_odt is not None
        }
        logger.info(f"Ingestor initialized. Parsers status: {self._parsers_status}")

    def process_file(self, file_path: str | Path) -> Generator[Dict[str, Any], None, None]:
        path = Path(file_path)
        if not path.exists():
            logger.error(f"File not found: {path}")
            return

        ext = path.suffix.lower()
        file_type = self.SUPPORTED_EXTENSIONS.get(ext)

        if not file_type:
            logger.warning(f"Unsupported file extension: {ext} for {path}")
            return

        content = ""
        metadata = {
            "source": str(path),
            "filename": path.name,
            "extension": ext,
            "file_type": file_type,
            "created_at": datetime.fromtimestamp(path.stat().st_ctime, tz=timezone.utc).isoformat(),
            "modified_at": datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat(),
            "size_bytes": path.stat().st_size
        }

        try:
            if file_type == "pdf":
                content = self._parse_pdf(path)
            elif file_type == "docx":
                content = self._parse_docx(path)
            elif file_type == "odt":
                content = self._parse_odt(path)
            else:
                content = self._parse_text(path)

            if not content.strip():
                logger.warning(f"No content extracted from {path}")
                return

            for chunk in self._semantic_chunking(content):
                yield {
                    "content": chunk,
                    "metadata": metadata,
                    "tags": ["file", f"type:{file_type}", f"ext:{ext}"]
                }

        except Exception as e:
            logger.error(f"Failed to process {path}: {e}")

    def _parse_pdf(self, path: Path) -> str:
        if not self._parsers_status["pdf"]:
            raise ImportError("PyMuPDF (fitz) not installed.")
        text = []
        with fitz.open(path) as doc:
            for page in doc:
                text.append(page.get_text())
        return "\n".join(text)

    def _parse_docx(self, path: Path) -> str:
        if not self._parsers_status["docx"]:
            raise ImportError("python-docx not installed.")
        doc = docx.Document(path)
        return "\n".join([p.text for p in doc.paragraphs])

    def _parse_odt(self, path: Path) -> str:
        if not self._parsers_status["odt"]:
            raise ImportError("odfpy not installed.")
        doc = load_odt(str(path))
        text = []
        for p in doc.getElementsByType(P):
            text.append(str(p))
        return "\n".join(text)

    def _parse_text(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return path.read_text(encoding="latin-1")

    def _semantic_chunking(self, text: str) -> Generator[str, None, None]:
        paragraphs = text.split("\n\n")
        current_chunk = []
        current_len = 0
        for p in paragraphs:
            p = p.strip()
            if not p:
                continue
            p_len = len(p)
            if current_len + p_len > self.chunk_size:
                if current_chunk:
                    yield "\n\n".join(current_chunk)
                    if self.overlap > 0:
                        current_chunk = [current_chunk[-1]]
                        current_len = len(current_chunk[0])
                    else:
                        current_chunk = []
                        current_len = 0
            current_chunk.append(p)
            current_len += p_len
        if current_chunk:
            yield "\n\n".join(current_chunk)
