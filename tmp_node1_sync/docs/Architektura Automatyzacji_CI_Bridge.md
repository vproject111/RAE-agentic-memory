  Architektura Automatyzacji (CI Bridge)

  Stworzyłem mechanizm "mostu" (CI Bridge), który pozwala lokalnemu agentowi AI (mnie, a w przyszłości Claude CLI) na interakcję z
  wynikami testów uruchamianych zdalnie w chmurze (GitHub Actions).

  1. Skrypt scripts/ci_bridge.py
  Jest to kluczowy element systemu. Skrypt ten wykonuje następujące zadania:
   * Pobieranie statusu: Odpytuje API GitHuba (via gh CLI) o status ostatniego workflow na danej gałęzi.
   * Identyfikacja porażki: Znajduje ostatnie nieudane uruchomienie (conclusion: failure).
   * Pobieranie logów: Ściąga surowe logi błędów (gh run view --log-failed), co pozwala agentowi AI "zobaczyć", co dokładnie poszło
     nie tak (np. komunikaty lintera, stack trace'y testów).
   * Pobieranie artefaktów: (Opcjonalnie) Pobiera pliki wygenerowane przez testy, np. raporty junit.xml, raporty pokrycia kodu czy
     zrzuty ekranu z testów UI.

  2. Workflow w GitHub Actions (.github/workflows/ci.yml)
  Skonfigurowałem workflow tak, aby był przyjazny dla tego procesu:
   * Fail-fast: Wyłączyłem fail-fast: false (strategia domyślna często przerywa inne joby, gdy jeden padnie, co utrudnia pełną
     diagnozę). W tym przypadku testy działają niezależnie.
   * Artefakty: Dodałem krok actions/upload-artifact, który zapisuje wyniki testów (junit.xml) i raporty (np. z ruff czy bandit),
     aby były dostępne do pobrania przez ci_bridge.py.
   * Formatowanie: Ujednoliciłem narzędzia (ruff, black, isort) w CI i lokalnie, aby uniknąć rozbieżności.

  3. Integracja z Agentem (Proces naprawczy)
  Schemat działania, który zastosowałem, wygląda następująco:
   1. Commit & Push: Wypycham zmiany do repozytorium.
   2. Wait & Check: Uruchamiam scripts/ci_bridge.py, który czeka na wynik CI.
   3. Analyze: Jeśli CI padnie, skrypt zwraca mi treść błędu (np. "file x.py line 10: unused import").
   4. Fix: Jako agent analizuję ten tekst, lokalizuję plik i wprowadzam poprawkę (np. replace).
   5. Loop: Powtarzam cykl.

  Czy Claude CLI może z tego korzystać?

  Tak, absolutnie.

  Ten schemat jest agnostyczny względem modelu AI. Opiera się na standardowych narzędziach systemowych (python, git, gh CLI), z
  których może korzystać każde narzędzie typu "AI coding assistant" (Claude CLI, GitHub Copilot CLI, Aider, itp.), o ile ma
  możliwość:
   1. Uruchamiania komend powłoki (run_shell_command).
   2. Odczytu wyjścia tych komend (read_file lub output komendy).
   3. Edycji plików (write_file/replace).

  Jak użyć tego z Claude CLI:
   1. Zainstaluj gh CLI i zaloguj się (gh auth login).
   2. Skopiuj scripts/ci_bridge.py do swojego projektu.
   3. Wydaj polecenie Claude'owi: "Uruchom `python scripts/ci_bridge.py`, przeanalizuj logi błędów i napraw kod."

  Claude wykona dokładnie te same kroki, co ja: uruchomi skrypt, przeczyta zwrócone logi (które są tekstem), zrozumie błąd i
  zaproponuje edycję pliku. To uniwersalny wzorzec "Agent-in-the-Loop" dla CI/CD.