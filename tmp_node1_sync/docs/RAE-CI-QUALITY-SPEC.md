RAE-CI-QUALITY-SPEC.md

Comprehensive CI Quality Governance for RAE
(version 1.0 — iterative, production-grade, aligned with RAE-TESTING-ZERO-WARNINGS)

1. Cele systemu jakości CI

Celem jest wprowadzenie systemu jakości, który:

gwarantuje brak dryfu jakościowego,

umożliwia pewne badania naukowe (OTel, math),

integruje się z architekturą czterech warstw pamięci RAE,

jest kompatybilny z podejściem local-first i agentami AI.

System obejmuje 4 filary:

Zero Warnings – żadne ostrzeżenie nie przechodzi.

Zero Flake – testy muszą być w 100% stabilne.

Zero Drift – brak regresji czasu, pamięci, kosztu, logów.

Auto-Healing CI – agent AI generuje poprawki i PR.

2. Filar 1: ZERO WARNINGS (obowiązkowy, iteracja 1)
Zasada:

Każdy warning = błąd. Blokuje merge.

Dotyczy:

testów (pytest),

linterów (ruff, mypy),

kompilacji (np. pydantic),

runtime logs (WARNING, ERROR, CRITICAL),

ostrzeżeń bibliotek zewnętrznych.

Konsekwencje:

PR z warningiem = 🚫 no merge

automatyczna adnotacja w CI

ticket automatycznie generowany do modułu (optional)

Wdrożenie:

ustaw -W error w pytest,

globalnie PYTHONWARNINGS=error,

filtr OTel dla logów.

➡ To jest PODSTAWA. Od tego zaczynasz. To wystarczy na start.

3. Filar 2: ZERO FLAKE (wprowadzić w iteracji 2)
Zasada:

Test niestabilny = wadliwy test. Musi zostać naprawiony albo trafia do kwarantanny.

Procedura:

test failuje losowo → CI oznacza go jako flaky

przenoszony jest do:
tests/quarantine/<module>/test_name.py

agent AI generuje propozycję poprawki

merge blokowany, dopóki flake nie zostanie naprawiony

Dlaczego?

Aby naukowcy i operatorzy mogli ufać metrykom RAE, testy muszą być deterministyczne.

4. Filar 3: ZERO DRIFT (iteracja 3–4)

(najbardziej "bigtech-level", optional ale daje przewagę naukową i biznesową)

Zasada:

„Kod nie może ulec pogorszeniu w żadnym wymiarze kosztowym.”

Dotyczy regresji:

czasu wykonania testów,

liczby alokacji pamięci,

głośności logów,

opóźnień API,

metryk OpenTelemetry w warstwie math i reflective.

Implementacja:

benchmark snapshot w repo (przechowywane w JSON)

każdy merge porównywany z poprzednią wersją

różnice > progów SLO → blokują CI

Przykład progów:

czas testów: +10% → FAIL

pamięć: +5% → FAIL

logi WARNING/ERROR > 0 → FAIL

math-layer OTel metrics > baseline × 1.05 → FAIL

5. Filar 4: Auto-Healing CI (agent AI)
Zasada:

„Każdy problem jakościowy generuje automatyczny PR z poprawką.”

Pipeline:

CI wykrywa warning, flake, drift → wygenerowanie pakietu kontekstu

agent AI (Gemini/Claude/Local LLM via Broker) generuje PR

PR trafia do review maintainerów (Ty lub inny człowiek)

merge po akceptacji

Przykład PR generowanego przez agenta:

poprawa importów,

stabilizacja testu,

zwiększenie timeoutów,

redukcja liczby allocacji,

poprawa walidacji w reflective API.

To jest „mądrzejsze niż BigTech”, bo integruje CI z czterowarstwową pamięcią RAE.

6. Model wdrażania – Iteracyjnie
Iteracja 1 (obowiązkowa)

✔ Zero Warnings
To jest minimalny, niezbędny krok.
Od tego zaczynasz. To wystarczy, żeby pipeline był stabilny.

Iteracja 2

✔ Zero Flake (duże podniesienie jakości)

Iteracja 3

✔ Zero Drift (podnosi jakość do poziomu OpenAI/DeepMind)

Iteracja 4

✔ Auto-healing CI (przewaga konkurencyjna RAE)

7. Kontekst: Integracja z RAE-TESTING-ZERO-WARNINGS

Plik ten rozszerza pierwotną politykę w sposób spójny z:

czterema warstwami pamięci RAE,

warstwą math,

OTel dla naukowców,

local-first architekturą,

wielomodelowym LLM brokerem.

8. Dlaczego to działa?

Każdy z filarów eliminuje inny rodzaj ryzyka:

Problem	Rozwiązanie
Ostrzeżenia → nieprzewidywalność	Zero Warnings
Niestabilne testy → fałszywe wyniki	Zero Flake
Regresje wydajności → rosnące koszty	Zero Drift
Koszt utrzymania → za wysoki	Auto-Healing CI