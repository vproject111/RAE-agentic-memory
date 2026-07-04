import os
import sys
from collections.abc import Callable, Iterable
from pathlib import Path

from gitignore_parser import parse_gitignore

# Katalogi, których NIE chcemy włączać do zrzutu, niezależnie od .gitignore
DEFAULT_IGNORED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    ".mypy_cache",
    ".pytest_cache",
    "dist",
    "build",
    ".idea",
    ".vscode",
}


def should_skip_dir(path: Path) -> bool:
    """Zwraca True, jeśli katalog powinien być pominięty."""
    return any(part in DEFAULT_IGNORED_DIRS for part in path.parts)


def iter_files(root_path: Path) -> Iterable[Path]:
    """
    Bezpieczny iterator po plikach w katalogu:
    - nie podąża za symlinkami do katalogów,
    - omija katalogi z DEFAULT_IGNORED_DIRS.
    """
    for dirpath, dirnames, filenames in os.walk(root_path, followlinks=False):
        current_dir = Path(dirpath)

        # odfiltruj katalogi, których nie chcemy przeglądać
        dirnames[:] = [d for d in dirnames if not should_skip_dir(current_dir / d)]

        for filename in filenames:
            yield current_dir / filename


def export_project(
    root_dir: str | Path, output_file: str | Path, max_file_size: int = 2 * 1024 * 1024
) -> None:
    """
    Zbiera zawartość projektu do jednego pliku tekstowego.

    :param root_dir: katalog projektu (np. ".")
    :param output_file: ścieżka do pliku wynikowego
    :param max_file_size: maksymalny rozmiar pojedynczego pliku (w bajtach),
                          powyżej tej wartości plik jest pomijany
    """
    root_path = Path(root_dir).resolve()
    output_path = Path(output_file).resolve()

    # Wczytaj i sparsuj .gitignore (jeśli istnieje)
    gitignore_file = root_path / ".gitignore"
    if gitignore_file.exists():
        matches: Callable[[str], bool] = parse_gitignore(str(gitignore_file))
    else:
        # jeśli nie ma gitignore – nic nie ignorujemy
        def matches(p: str) -> bool:  # type: ignore[misc]
            return False

    with output_path.open("w", encoding="utf-8") as out:
        for path in sorted(iter_files(root_path)):
            # pomiń sam plik wynikowy, żeby nie wciągać go do środka
            if path.resolve() == output_path:
                continue

            # ścieżka relatywna względem root_path
            rel_path = path.relative_to(root_path)

            # pomijamy pliki ignorowane przez .gitignore
            # UWAGA: parse_gitignore zwykle oczekuje ścieżek
            # względem katalogu z .gitignore, więc przekazujemy
            # ścieżkę relatywną jako string
            if matches(str(rel_path)):
                continue

            # pomijamy bardzo duże pliki (np. modele, archiwa, logi)
            try:
                size = path.stat().st_size
            except OSError as e:
                print(
                    f"[WARN] Nie mogę odczytać rozmiaru pliku {rel_path}: {e}",
                    file=sys.stderr,
                )
                continue

            if size > max_file_size:
                print(
                    f"[INFO] Pomijam duży plik (> {max_file_size} B): {rel_path}",
                    file=sys.stderr,
                )
                continue

            # próbujemy czytać jako tekst UTF-8, ignorując błędy
            try:
                with path.open("r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception as e:  # np. permissions, dziwny path, itp.
                print(
                    f"[WARN] Nie mogę odczytać pliku {rel_path}: {e}", file=sys.stderr
                )
                continue

            out.write(f"# {rel_path}\n")
            out.write(content)
            out.write("\n\n")

    print(f"Zapisano pliki do {output_path}")


if __name__ == "__main__":
    # Jeśli chcesz, możesz podać argumenty z CLI:
    # python eptt.py . project_dump.txt
    if len(sys.argv) >= 3:
        root = sys.argv[1]
        out_file = sys.argv[2]
    else:
        root = "."
        out_file = "project_dump.txt"

    export_project(root_dir=root, output_file=out_file)
