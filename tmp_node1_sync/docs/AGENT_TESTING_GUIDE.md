AGENT_TESTING_GUIDE.md

Test Development & Maintenance Guide for RAE Agentic Memory
(Polityka ZERO WARNINGÓW + zasady dla agentów AI)

1. Cel dokumentu

Ten dokument definiuje jednolitą strategię tworzenia i utrzymania testów w projekcie RAE-agentic-memory, w tym:

politykę ZERO WARNINGÓW podczas uruchamiania testów,

zasady pisania testów dla agentów AI (małe modele, średnie modele, modele „duże” / reasoning),

zasady usuwania ostrzeżeń z kodu i bibliotek,

wymogi, które musi spełniać kod testowy, aby przeszedł przez CI,

preferowany styl i strukturę testów,

standardy maintainability i czytelności.

Celem jest zapewnienie maksymalnej jakości kodu, pełnej powtarzalności wyników oraz zgodności z praktykami wymaganymi w środowiskach naukowych, przemysłowych i administracji publicznej.

2. Zasada nadrzędna: ZERO WARNINGÓW

W projekcie RAE obowiązuje polityka:

Wszystkie testy muszą przechodzić bez jakichkolwiek ostrzeżeń.
CI uruchamia testy w trybie pytest -W error.

2.1 Co oznacza ZERO WARNINGÓW?

Każdy ostrzeżenie jest traktowane jak błąd testu.

Ostrzeżenia pochodzące z kodu RAE muszą zostać usunięte – przez poprawę testu lub kodu produkcyjnego.

Ostrzeżenia z bibliotek zewnętrznych:

najpierw próbujemy wyeliminować poprawnym użyciem API,

jeśli nie jest to możliwe – dodajemy świadomy filtr z komentarzem wyjaśniającym.

Jeżeli dana funkcja ma celowo rzucać ostrzeżenie, test musi używać:

with pytest.warns(ExpectedWarningClass, match="treść"):
    ...


i nie może generować ostrzeżenia w logach globalnych.

Każda zmiana testów lub kodu produkcyjnego musi przechodzić:

pytest -W error

3. Wymagania techniczne w CI

W pipeline CI obowiązuje:

- name: Run tests with warnings as errors
  run: pytest -W error --maxfail=1 --disable-warnings


W pytest.ini:

[pytest]
filterwarnings =
    error
    # Dopuszczone ostrzeżenia (TYLKO w przypadku gdy nie ma alternatywy, każde z komentarzem):
    # ignore:Some known benign warning:some.external.module

4. Zasady pisania testów (dla agentów i ludzi)
4.1 Zasady ogólne

Testy muszą być deterministyczne – bez losowości bez seeda, bez zależności od zewnętrznych usług, czasu systemowego itd.

Testy nie mogą pozostawiać warningów – polityka ZERO WARNINGÓW.

Każdy test musi być czytelny i prosty – preferujemy:

jasne nazw plików: test_<moduł>.py,

jasne nazwy testów: test_<funkcja>_<zachowanie>.

Testy powinny korzystać z fixtures zamiast duplikacji danych.

Testy powinny sprawdzać również przypadki brzegowe, błędy i wyjątki.

Testy nie zmieniają architektury systemu – mogą wymagać refaktoringu kodu, ale nie zmieniają API, chyba że to absolutnie konieczne.

5. Zasady specyficzne dla agentów AI

Agentom należy przekazywać wyraźne instrukcje, aby:

nie ignorowały ostrzeżeń,

traktowały warningi jak błędy,

preferowały refaktoryzację kodu zamiast maskowania problemu,

stosowały pytest.warns gdy ostrzeżenie jest spodziewane,

używały filtrów ostrzeżeń tylko świadomie i tylko z komentarzem.

6. Instrukcje dla agentów – NOWE TESTY
Wklej ten blok do promptów generujących testy:
AGENT MODE – NEW TESTS

Projekt: RAE-agentic-memory
Polityka: ZERO WARNINGÓW
CI: pytest -W error

Twoje zadanie:

Napisz testy w pytest dla modułu:
<tu wstaw ścieżkę i opis funkcji>

Zastosuj poniższe zasady:

Testy muszą przechodzić bez ostrzeżeń (pytest -W error).

Ostrzeżenia traktuj jak błędy – popraw kod lub sposób użycia API.

Jeśli testuje się zachowanie rzucające ostrzeżenie, użyj pytest.warns(...).

Jeśli biblioteka zewnętrzna generuje warning, a nie można tego naprawić:

dodaj filtr (pytest.ini lub pytest.mark.filterwarnings)

dodaj komentarz wyjaśniający.

Używaj fixtures do usuwania duplikacji.

Zachowuj istniejące nazwy funkcji i modułów.

Zwróć:

pełny kod pliku z testami,

ewentualne poprawki w module,

ewentualną zmianę w pytest.ini.

7. Instrukcje dla agentów – NAPRAWA ISTNIEJĄCYCH TESTÓW
Wklej ten blok do promptu refaktorującego testy:
AGENT MODE – FIX TEST WARNINGS

Projekt: RAE-agentic-memory
Polityka: ZERO WARNINGÓW
Tryb CI: pytest -W error

Twoje zadanie:

Przeanalizuj logi testów i znajdź wszystkie warningi.

Dla każdego warningu:

jeśli pochodzi z kodu RAE – popraw kod lub test tak, by warning zniknął,

jeśli pochodzi z biblioteki i nie da się tego uniknąć:

zaproponuj świadomy filtr w pytest.ini lub pytest.mark.filterwarnings,

dodaj komentarz DLACZEGO filtr jest potrzebny.

Testy mają przechodzić w trybie pytest -W error.

Zwróć:

poprawione testy,

poprawiony kod,

ewentualne zmiany w pytest.ini.

8. Instrukcje dla dużych modeli reasoning

Te modele mogą wykonać zadania dodatkowe:

ograniczyć duplikację testów,

wprowadzić lepsze fixture’y,

uporządkować strukturę katalogów testowych,

wykryć niepotrzebne testy,

sugerować lepsze abstrakcje testowe,

uspójnić nazwy testów z nazwami modułów.

Blok prompta:
ADVANCED AGENT MODE – TEST REFACTOR & CLEANUP

Dodatkowe zadania:

Zidentyfikuj duplikację testów i zaproponuj lepsze fixture’y.

Uporządkuj strukturę katalogów w tests/, jeśli to zwiększy czytelność.

Zachowaj zgodność z polityką ZERO WARNINGÓW.

Nie zmieniaj publicznego API modułów, chyba że to absolutnie konieczne.

9. Przykłady najlepszych praktyk
9.1 Poprawnie testowane ostrzeżenie
import pytest
import warnings

def test_warns_properly():
    with pytest.warns(UserWarning, match="deprecated"):
        warnings.warn("deprecated", UserWarning)

9.2 Zły przykład (NIEDOZWOLONE)
def test_throws_warning():
    import warnings
    warnings.warn("deprecated")  # ❌ warning wyleci do logów

10. Minimalny szablon pliku testowego
import pytest
from app.module import function

def test_function_happy_path():
    result = function(...)
    assert result == ...

def test_function_edge_case():
    ...

def test_function_error():
    with pytest.raises(SomeError):
        function(...)

11. Podsumowanie

Polityka ZERO WARNINGÓW:

zwiększa jakość kodu,

usuwa „szum” z logów,

jest idealna pod środowiska naukowe, przemysłowe i administrację,

pomaga agentom AI pisać spójne testy,

ułatwia długoterminowe utrzymanie projektu RAE.