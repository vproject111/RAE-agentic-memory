PLAN_9of5_BENCHMARKS.md
RAE Benchmarking Roadmap – 9/5 Quality Level
Complete plan to elevate RAE benchmarks beyond academic, enterprise, and OSS standards
🎯 Cel dokumentu

Celem tego planu jest doprowadzenie modułu Benchmarking & Evaluation w projekcie RAE – Reflective Agentic-memory Engine do poziomu:

🔥 9/5 (ponadidealnego)

czyli:

przewyższającego standard laboratoriów AI,

przygotowanego do walidacji naukowej,

akceptowalnego dla działów R&D (Canon, Minolta, Motorola, AbakusAI),

w pełni reproducible,

z automatyzacją, metrykami i raportami jak z profesjonalnego research pipeline'u.

Po wdrożeniu benchmarków w tej formie RAE staje się:

✔ produktem badawczym,
✔ produktem enterprise,
✔ platformą współpracy z Bielik.ai,
✔ platformą publikacji naukowych,
✔ kandydatem do adopcji w systemach agentowych.

🧱 1. Architektura Benchmarkingu 9/5 – docelowy układ katalogów
benchmarking/
│
├── PLAN_9of5_BENCHMARKS.md        ← ten dokument
├── BENCHMARK_STARTER.md
├── BENCHMARK_REPORT_TEMPLATE.md
│
├── sets/                          ← Wszystkie zestawy danych
│   ├── academic_lite.yaml
│   ├── academic_extended.yaml
│   ├── industrial_small.yaml
│   ├── industrial_large.yaml
│   └── stress_memory_drift.yaml
│
├── scripts/                       ← Silniki benchmarków
│   ├── run_benchmark.py
│   ├── compare_runs.py
│   ├── generate_plots.py
│   └── profile_latency.py
│
└── results/
    ├── example_report_academic.md
    ├── example_report_industrial.md
    └── metrics_reference.json

🧪 2. Zakres Benchmarków – Co RAE musi mierzyć, by osiągnąć poziom 9/5
2.1 Metryki jakości pamięci (Core AI Memory Metrics)

HitRate@k

MRR (Mean Reciprocal Rank)

Top-k Retrieval Accuracy

Semantic Similarity Score

Graph Alignment Precision

Reflection Improvement Delta
→ różnica MRR przed/po refleksji

2.2 Metryki wydajnościowe

Średnia latencja

P95 / P99 latencja

Throughput (zapytania/s)

Czas indeksacji pamięci

Czas aktualizacji grafu wiedzy

Koszt tokenów (jeśli refleksja używa LLM)

2.3 Metryki stabilności pamięci

Memory Drift Score
→ czy pamięć zaczyna żyć własnym życiem

Compression Fidelity
→ jakość po summarization/pruning

Graph Integrity Ratio

2.4 Metryki systemowe (OpenTelemetry)

CPU per benchmark

RAM peak usage

I/O overhead

czas GC

footprint pamięci trwałej (Postgres/Qdrant)

🚀 3. Zestawy Benchmarków – 5 oficjalnych datasetów RAE
🔹 3.1 academic_lite.yaml

3–5 memories

5 queries

czas uruchomienia: < 5 sekund

cel: sanity check

🔹 3.2 academic_extended.yaml

25–50 memories

20 queries

mix semantyczny, pytania podchwytliwe

cel: walidacja naukowa

🔹 3.3 industrial_small.yaml

100–300 memories

realne, nieczyste dane

cel: testy R&D / PoC

🔹 3.4 industrial_large.yaml

1k–5k memories

100–200 queries

stres pamięci, skalowanie

cel: testy enterprise

🔹 3.5 stress_memory_drift.yaml

refleksja co X kroków

zapis przed i po

cel: mierzenie stabilności i dryfu pamięci

🔧 4. Automatyzacja – Kluczowe narzędzia
4.1 run_benchmark.py

Implementuje:

ładowanie YAML

insert memories

wykonanie queries

zbieranie metryk

zapis do JSON i MD

4.2 compare_runs.py

Porównuje:

MRR

HitRate

latencję

reflection delta

Wynik: tabela + rekomendacja
(w stylu: „config B poprawia MRR o 12% kosztem +5 ms latencji”)

4.3 profile_latency.py

100 powtórzeń wybranego query

dystrybucja wyników

histogram

4.4 generate_plots.py (opcjonalnie)

Tworzy wykresy dla:

MRR zmian modułów pamięci

latencji

memory drift

reflection gains

📈 5. Workflow CI/CD – Benchmark jako strażnik jakości

Dodaj w .github/workflows/ci.yml:

✨ benchmark-smoke-test

odpala academic_lite.yaml

limit: 20 sekund

warunek PR: MRR >= baseline

zatrzymuje regresje

✨ benchmark-nightly

odpala wszystkie zestawy

generuje raport do results/

archiwizuje metryki

w przyszłości → dashboard

📊 6. Dokumentacja – 3 pliki, które decydują o jakości 9/5
✔ BENCHMARK_STARTER.md

– format YAML
– przykłady
– wyjaśnienia metryk

✔ BENCHMARK_REPORT_TEMPLATE.md

– opis eksperymentu
– tabela wyników
– sekcja obserwacji
– sekcja rekomendacji

✔ example_report_academic.md

– pokazuje, jak wygląda idealny raport naukowy

🏁 7. Etapy wdrożenia – plan wykonania
ETAP 1 – Struktura i zestawy

(1–2 dni)

stworzenie sets/

dodanie 3 pierwszych benchmarków

dodanie Starter + Template

ETAP 2 – Skrypty

(2–3 dni)

implementacja run_benchmark.py

implementacja compare_runs.py

ETAP 3 – CI/CD + Makefile

(1 dzień)

make benchmark-lite

make benchmark-academic

job benchmark-smoke

ETAP 4 – Raporty i pierwsze wyniki

(1 dzień)

wygenerowanie example report

zapis reference metrics

ETAP 5 – Dopracowanie do 9/5

(3–5 dni)

memory drift benchmark

reflection delta measurement

stress tests

dashboard dla wszystkich opcji

🏆 8. Kryteria osiągnięcia poziomu 9/5

✔ RAE posiada 5 oficjalnych benchmarków
✔ Benchmarki są powtarzalne, deterministyczne, opisane
✔ Benchmarki są automatyczne (Makefile + CI)
✔ Benchmarki mają raporty, pliki wynikowe i metryki referencyjne
✔ RAE mierzy reflection delta i memory drift
✔ Modele pamięci mają mierzalną przewagę nad RAG
✔ Na podstawie benchmarków można tworzyć publikacje naukowe
✔ Benchmarking jest łatwy dla uczelni, labów i firm R&D

🎉 9. Efekt końcowy

Po wdrożeniu tego planu RAE jest:

najlepiej zmierzonym memory engine’m w Polsce,

jednym z najlepiej opisanych OSS memory engines globalnie,

gotowy do współpracy z Bielik.ai, AGH, PK, UJ, AbakusAI,

gotowy do publikacji arXiv,

gotowy do rozmów inwestycyjnych i komercjalizacji.

Benchmarking na poziomie 9/5 robi z RAE:

👉 standard referencyjny
👉 produkt enterprise
👉 platformę naukową