Self-Documenting Codebase Blueprint

  Model "Samodokumentującego się Kodu" to strategia automatyzacji utrzymania dokumentacji technicznej, która minimalizuje wysiłek
  deweloperów i zapewnia, że dokumentacja jest zawsze zgodna z rzeczywistym stanem projektu.

  Kluczową zasadą jest: Źródłem prawdy jest kod i historia wersji (Git). Dokumentacja jest tylko ich pochodną (widokiem).

  1. Architektura Systemu

  System składa się z trzech warstw:
   1. Warstwa Źródłowa: Kod, Komentarze TODO, Historia Gita (Commity).
   2. Warstwa Przetwarzania: Skrypty automatyzujące (Automator).
   3. Warstwa Prezentacji: Pliki Markdown (STATUS.md, CHANGELOG.md, TODO.md).

  2. Standardy (Wymagania Wstępne)

  Aby automatyzacja działała, zespół musi przestrzegać prostych reguł:

  A. Conventional Commits
  Każdy commit musi zaczynać się od typu:
   * feat: - nowa funkcjonalność.
   * fix: - naprawa błędu.
   * docs: - zmiany w dokumentacji.
   * refactor: - zmiany w kodzie bez zmiany funkcjonalności.
   * test:, chore:, perf: - inne.

  Przykład: feat(auth): add JWT login support

  B. Komentarze w Kodzie (TODO)
  Dług techniczny oznaczamy w kodzie, a nie w zewnętrznych systemach (na etapie kodu).
  Format: # TODO: opis zadania lub // TODO: opis zadania.

  3. Narzędzie: docs_automator.py

  Jest to skrypt (można go napisać w Pythonie/Bashu/Go), który uruchamiany jest lokalnie przed release'em lub w CI/CD po merge'u do
  głównej gałęzi.

  Funkcje Skryptu:

   1. Generator Changeloga (`CHANGELOG.md`):
       * Czyta git log od ostatniego wydania.
       * Parsuje prefiksy (feat, fix).
       * Grupuje zmiany w sekcje: Added, Fixed, Changed.
       * Dopisuje nową sekcję ## [Unreleased] na górze pliku.

   2. Skaner Długu Technicznego (`TODO.md`):
       * Przeszukuje wszystkie pliki źródłowe (z wyłączeniem vendor/node_modules).
       * Wyciąga linie zawierające TODO.
       * Generuje listę: - [ ] plik:linia - opis.
       * Dzięki temu PM/Tech Lead widzi dług techniczny bez zaglądania w kod.

   3. Dashboard Projektu (`STATUS.md`):
       * Pobiera status CI (np. z GitHub Actions Badge).
       * Pobiera wersję języka/zależności (np. z pyproject.toml lub package.json).
       * Generuje plik z "zielonymi/czerwonymi" lampkami, dając szybki wgląd w zdrowie projektu.

  4. Wdrożenie w Nowym Projekcie

  Aby przenieść ten model do innego projektu:

   1. Skopiuj skrypt: Przenieś scripts/docs_automator.py do katalogu ze skryptami.
   2. Dodaj do CI: W .github/workflows/ci.yml (lub innym CI) dodaj krok, który uruchamia skrypt i commituje zmiany (jeśli chcesz
      pełnej automatyzacji) lub uruchamiaj go ręcznie jako make docs.
   3. Zaktualizuj `.gitignore`: Upewnij się, że generowane pliki NIE są ignorowane (chcemy je w repozytorium).

  5. Korzyści Biznesowe

   * Oszczędność czasu: Deweloper nie musi pisać Changeloga ręcznie.
   * Aktualność: Dokumentacja nigdy nie "gnije" (drift documentation).
   * Transparentność: Klient/Manager widzi postępy (CHANGELOG) i problemy (TODO) w prostych plikach tekstowych.
   * AI-Ready: Taka struktura jest idealna dla Agentów AI (jak ja czy Claude), które mogą szybko zrozumieć stan projektu, czytając
     tylko te 3 pliki.
