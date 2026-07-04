import subprocess
import logging
import json
from pathlib import Path
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

class LlamaCppAdapter:
    """Adapter dla silnika llama.cpp (llama-cli.exe) dla RAE-Windows."""

    def __init__(self, llama_path: Path, model_path: Optional[Path] = None, profile: str = "A"):
        self.llama_path = llama_path
        self.model_path = model_path
        self.profile = profile
        self.is_available = self.llama_path.exists() and self.model_path and self.model_path.exists()

    def generate(self, prompt: str, max_tokens: int = 128, temperature: float = 0.7) -> str:
        """Generuje tekst przy użyciu lokalnej binarki llama-cli."""
        if not self.is_available:
            logger.warning("LLM nie jest dostępny (brak binarki lub modelu).")
            return ""

        cmd = [
            str(self.llama_path),
            "-m", str(self.model_path),
            "-p", prompt,
            "-n", str(max_tokens),
            "--temp", str(temperature),
            "--simple-io",
            "--log-disable"
        ]

        # Dodaj flagi GPU dla profilu D
        if self.profile == "D":
            cmd.extend(["-ngl", "99"]) # Offload layers to GPU

        try:
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=60
            )
            if process.returncode == 0:
                # llama-cli często zwraca prompt + odpowiedź, wycinamy prompt
                full_output = process.stdout.strip()
                if full_output.startswith(prompt):
                    return full_output[len(prompt):].strip()
                return full_output
            else:
                logger.error(f"Błąd llama-cli: {process.stderr}")
        except subprocess.TimeoutExpired:
            logger.error("Przekroczono limit czasu dla LLM.")
        except Exception as e:
            logger.error(f"Wyjątek podczas wywołania LLM: {e}")
        
        return ""

    def normalize_query(self, query: str) -> str:
        """Używa LLM do przekształcenia zapytania użytkownika w słowa kluczowe dla FTS."""
        if self.profile == "A" or not self.is_available:
            return query # Fallback do oryginalnego zapytania

        prompt = f"System: Jesteś asystentem wyszukiwania. Wyodrębnij słowa kluczowe z zapytania dla bazy danych.\nUser: {query}\nKeywords:"
        result = self.generate(prompt, max_tokens=32)
        return result if result else query

    def format_results(self, query: str, memories: List[Dict[str, Any]]) -> str:
        """Podsumowuje wyniki wyszukiwania w spójną odpowiedź."""
        if self.profile == "A" or not self.is_available or not memories:
            return ""

        context = "\n".join([f"- {m['content']}" for m in memories[:5]])
        prompt = f"System: Odpowiedz na zapytanie użytkownika na podstawie podanych wspomnień.\nKontekst:\n{context}\n\nUser: {query}\nOdpowiedź:"
        return self.generate(prompt, max_tokens=256)
