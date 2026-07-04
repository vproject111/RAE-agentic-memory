RAE-CI-QUALITY-SPEC-enterprise-v2.0.md

Plik możesz umieścić np. w docs/RAE-CI-QUALITY-SPEC-enterprise-v2.0.md.
To jest rozszerzenie v1.0 o SLO/SLA, BigTech-comparison i diagram.

# RAE CI Quality Governance – Enterprise v2.0

## 0. Cel dokumentu

Ten dokument opisuje **enterprise’ową** politykę jakości CI/CD dla projektu **RAE-agentic-memory**, przeznaczoną dla:

- zespołów R&D (uczelnie, laby AI),
- partnerów przemysłowych (produkcja, administracja publiczna),
- audytorów bezpieczeństwa i zgodności (ISO 42001, 27001, regulacje branżowe).

Polityka opiera się na czterech filarach:

1. **Zero Warnings**
2. **Zero Flake**
3. **Zero Drift**
4. **Auto-Healing CI (agent-assisted)**

i jest spójna z:
- architekturą **czterech warstw pamięci RAE**,
- warstwą math,
- OpenTelemetry,
- modelem **local-first** oraz wielomodelowym brokerem LLM.

---

## 1. Diagram – Przepływ CI z jakością

```mermaid
flowchart TD

A[Commit / Pull Request] --> B[GitHub Actions CI]

B --> C1[Lint + Format\n(ruff, black)]
B --> C2[Type Check\n(mypy)]
B --> C3[Tests\n(pytest -W error)]
B --> C4[Arch/Contract Tests]
B --> C5[Telemetry Check\n(Zero Drift)]

C1 --> D{Zero Warnings?}
C2 --> D
C3 --> D
C4 --> D
C5 --> D

D -->|NO| E[Fail CI\nGenerate Issue + Context]
D -->|YES| F[CI Passed]

E --> G[AI Fix Agent\n(Gemini/Claude/Local LLM)]
G --> H[Auto PR with Fix]
H --> B

F --> I[Merge to main/develop]

2. SLO / SLA dla jakości
2.1. SLO – cele jakościowe
Obszar	SLO (cel)
Warnings	0 warnings w CI i w testach
Flaky tests	0 testów flaky w gałęzi main
Drift wydajności	≤ 5% wzrostu czasu/pamięci między releasami
Logi WARNING/ERROR	0 w testach oraz smoke testach CI
Pokrycie krytycznych modułów	≥ 80% coverage dla warstw math + reflective
2.2. SLA – zobowiązania utrzymaniowe

Na potrzeby umów/pilotów można przyjąć:

SLA-1 (warnings): każdy nowy warning wykryty w main → naprawa w ciągu 3 dni roboczych.

SLA-2 (flake): każdy flaky test w main → naprawa lub kwarantanna w ciągu 5 dni roboczych.

SLA-3 (drift): regresja > 10% w czasie/pamięci → ticket P1 i plan naprawczy ≤ 7 dni.

SLA-4 (security/logs): logi z kategorią ERROR/CRITICAL w cyklu testowym → natychmiastowy blok release’a.

3. Filar 1 – Zero Warnings

(skrótowo, bo pełny opis jest w wersji v1.0; tutaj pod kątem enterprise)

Każdy warning jest traktowany jako błąd jakości i blokuje merge.

Dotyczy:

testów (pytest),

linterów (ruff, mypy),

kompilacji / uruchomienia,

logów WARNING/ERROR z modułów krytycznych.

Dla partnerów:
zero warnings oznacza, że każda wersja RAE jest przewidywalna i łatwa do audytu.

4. Filar 2 – Zero Flake

CI utrzymuje listę testów oznaczonych jako flaky (np. tag @pytest.mark.flaky albo dedykowany raport).

Test, który failuje losowo:

jest automatycznie oznaczany,

przenoszony do katalogu tests/quarantine/,

otwierany jest ticket dla odpowiedzialnego modułu.

Korzyść dla naukowców:
wyniki eksperymentów nie są zanieczyszczone losową niestabilnością.

5. Filar 3 – Zero Drift

Zero Drift to mechanizm kontroli regresji wydajności, kosztów i hałasu logów.

5.1. Zakres monitorowanych metryk

Czas wykonania kluczowych testów (math/reflective/API).

Zużycie pamięci (np. poprzez integration z OTel / profilerem).

Liczba logów na poziomach:

INFO,

WARNING,

ERROR,

CRITICAL.

Metryki math-layer (np. liczba wierzchołków grafu, czas PageRank, koszt zapytań do wektorów).

Metryki reflective-layer (np. czas pętli refleksji, liczba kroków per epizod).

5.2. Progi (przykład do dopracowania per projekt)

Czas testów math: wzrost > 5% między kolejnymi releasami → FAIL CI.

Pamięć: wzrost > 10% w benchmarku → FAIL.

Logi WARNING/ERROR: > 0 w testach → FAIL.

API latency (p95): wzrost > 20% vs poprzednia wersja → FAIL.

6. Filar 4 – Auto-Healing CI (Agent-Assisted)
6.1. Idea

Zamiast tylko blokować CI, system:

Gromadzi kontekst błędu (diff, logi, konfigurację).

Przekazuje go do agenta AI (np. RAE + zewnętrzny LLM).

Agent proponuje pull request z poprawką:

naprawa testu,

ograniczenie hałasu logów,

refaktoryzacja pod typy,

optymalizacja math-core.

6.2. Przepływ

CI wykrywa problem (warning, flake, drift).

Generator kontekstu buduje pakiet:

zmienione pliki,

logi z danego joba,

metryki z OTel (jeśli dotyczy).

Agent AI tworzy branch fix/auto/<id> + PR.

Człowiek akceptuje/odrzuca PR (human-in-the-loop).

7. Porównanie do praktyk BigTech

Google / DeepMind:

zero warnings, mocny nacisk na coverage i obowiązkowe review.

OpenAI:

kontrola driftu, telemetry-driven, focus na bezpieczeństwo.

AWS:

obserwowalność, SLO/SLA, „operational excellence” (Well-Architected).

RAE enterprise v2.0:

łączy wszystkie te podejścia z:

czterowarstwową pamięcią,

hybrydową warstwą math,

lokalnym / hybrydowym modelem AI do auto-naprawy.

To daje poziom jakości, który można bronić zarówno w przemyśle, jak i w publikacjach naukowych.

8. Podsumowanie

Ten dokument stanowi:

specyfikację dla zespołów wdrażających RAE w środowiskach produkcyjnych,

punkt odniesienia dla audytów jakości,

bazę pod opisy w umowach, pilotach i artykułach naukowych.

Rekomendowana ścieżka:

Etap 1: wdrożyć Zero Warnings (CI już przygotowane).

Etap 2: wprowadzić Zero Flake.

Etap 3: dodać Zero Drift z metrykami OTel.

Etap 4: uruchomić Auto-Healing CI z agentami AI.