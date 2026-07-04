# INSTRUKCJA DLA AGENTÓW: TESTY JAKO KONTRAKT, NIE SNAPSHOT KODU

> **⚠️ UWAGA**: Ten dokument opisuje filozofię testów (RULE #7). Dla pełnego workflow testowania zobacz:
> - **[CRITICAL_AGENT_RULES.md](../CRITICAL_AGENT_RULES.md)** - 8 obowiązkowych zasad
> - Sekcja poniżej: "3-Fazowy Workflow Testowania"

---

## 🔄 3-Fazowy Workflow Testowania

**KRYTYCZNE**: Różne fazy projektu = różne poziomy testowania!

```
┌─────────────────────────────────────────────────────────┐
│ PHASE 1: FEATURE BRANCH                                 │
│ ✅ Test ONLY your new code                              │
│ ✅ Command: pytest --no-cov path/to/test_yourcode.py   │
│ ✅ Why: Fast feedback (seconds, not minutes)            │
│ ❌ NEVER: pytest (full suite) or make test-unit         │
├─────────────────────────────────────────────────────────┤
│ PHASE 2: DEVELOP BRANCH (MANDATORY!)                   │
│ ✅ After merge: make test-unit (FULL test suite)       │
│ ✅ After merge: make lint                              │
│ ✅ MUST PASS before proceeding to main                 │
│ ❌ If fails: FIX on develop, don't proceed to main     │
├─────────────────────────────────────────────────────────┤
│ PHASE 3: MAIN BRANCH                                   │
│ ✅ CI tests automatically (GitHub Actions)             │
│ ✅ Must always stay green                              │
│ ❌ NEVER push to main with failing tests               │
└─────────────────────────────────────────────────────────┘
```

### Przykład workflow:

```bash
# PHASE 1: Feature branch - test ONLY your new code
git checkout -b feature/new-feature
# ... write code ...
pytest --no-cov apps/memory_api/tests/test_my_new_feature.py
make format && make lint
git commit -m "feat: add new feature"

# PHASE 2: Develop - FULL tests MANDATORY!
git checkout develop
git merge feature/new-feature --no-ff
make test-unit   # ← OBOWIĄZKOWE! Musi przejść!
make lint
# If pass → proceed to main
# If fail → FIX on develop first!

# PHASE 3: Main - CI automatic
git checkout main
git merge develop --no-ff
git push origin main develop
# CI runs full tests automatically
```

---

## Zasada ogólna:
Traktuj testy jako kontrakt zachowania systemu, a nie jako wierne odbicie aktualnej implementacji.

1. Co testy MAJĄ sprawdzać

Pisząc lub poprawiając testy:

Skupiaj się na publicznym zachowaniu:

wejście → wyjście,

publiczne API (funkcje, endpointy, komendy CLI),

poprawną obsługę błędów i wyjątków.

Sprawdzaj:

czy funkcja zwraca poprawne dane,

czy serwis poprawnie reaguje na różne przypadki brzegowe,

czy system zachowuje się zgodnie z opisem w dokumentacji/specyfikacji.

Nigdy nie dopasowuj testów do ewidentnie błędnego zachowania tylko po to, żeby „były na zielono”.

2. Czego testy NIE powinny robić

Unikaj pisania testów, które:

zależą od szczegółów implementacyjnych, np.:

konkretnego układu wewnętrznych wywołań funkcji,

struktury plików i modułów,

nazw prywatnych funkcji/metod,

wewnętrznych optymalizacji, cache’y, itp.

łamią się przy każdej kosmetycznej zmianie kodu (refaktor bez zmiany zachowania).

odtwarzają logikę produkcyjną 1:1 w teście (duplikacja algorytmu).

Testy mają „patrzeć z zewnątrz”, jak użytkownik / klient API, nie jak debugger.

3. Kiedy wolno zmieniać testy

Agent może zmodyfikować testy, jeżeli:

Zmieniła się specyfikacja lub oczekiwane zachowanie
– np. poprawiony bug, zmienione reguły biznesowe, nowe wymagania.

Test był błędny lub zbyt kruchy
– test łamał się przy refaktorze, mimo że zachowanie systemu pozostało poprawne.

Test był powiązany z detalami implementacji, a celem refaktoru jest od nich odejście.

W takich przypadkach:

zaktualizuj test tak, by odzwierciedlał aktualny, poprawny kontrakt,

nie usuwaj testów „dla świętego spokoju” – zastąp je lepszymi.

4. Kiedy NIE wolno zmieniać testów

Agent nie powinien zmieniać testów, jeśli:

test poprawnie opisuje oczekiwane zachowanie z punktu widzenia użytkownika / systemu,

zmiany w kodzie są tylko refaktoryzacją struktury i nie miały zmieniać logiki,

jedynym powodem zmiany testu byłoby „pozbycie się czerwonego wyniku” bez zrozumienia przyczyny.

W takim przypadku:

traktuj czerwony test jako sygnał błędu w kodzie,

popraw kod tak, aby test znów przechodził.

5. Relacja refaktor → testy

Przy każdej zmianie:

Jeśli zmieniasz logikę / zachowanie:

oczekuj, że część testów się wywali,

zaktualizuj testy tak, żeby odzwierciedlały nowy, poprawny kontrakt.

Jeśli robisz czysty refaktor (zmiana struktury bez zmiany zachowania):

testy powinny przejść bez zmian albo wymagać co najwyżej korekty importów,

jeśli łamią się masowo → to znak, że były źle zaprojektowane (zbyt związane z implementacją).