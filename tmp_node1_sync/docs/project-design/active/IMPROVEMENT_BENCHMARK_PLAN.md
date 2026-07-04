IMPROVEMENT_PLAN.md
RAE Benchmarking – Upgrade Plan (Target Quality: 6/5)
Complete roadmap for transforming RAE benchmarks into an academic- and enterprise-grade evaluation suite
🎯 Cel dokumentu

Celem tego planu jest podniesienie modułu Benchmarking & Evaluation w projekcie RAE do poziomu:

standardu akademickiego (AGH, PK, UJ, conference-level reproducibility),

standardu korporacyjnego (Canon R&D, Minolta Labs, Motorola, AbakusAI),

standardu open-source premium (czytelna struktura, łatwy start, gotowe zestawy).

Po wdrożeniu wszystkich punktów, projekt osiąga poziom 6/5:

Benchmarking nie jest dodatkiem — benchmarking staje się pełnoprawnym produktem w produkcie.

🧱 1. Struktura katalogów – docelowy układ
benchmarking/
│
├── BENCHMARK_STARTER.md
├── BENCHMARK_REPORT_TEMPLATE.md
├── IMPROVEMENT_PLAN.md  ← ten plik
│
├── sets/
│   ├── academic_lite.yaml
│   ├── academic_extended.yaml
│   ├── industrial_small.yaml
│   └── industrial_large_template.yaml
│
├── scripts/
│   ├── run_benchmark.py
│   ├── compare_runs.py
│   └── plot_metrics.py   (opcjonalne)
│
└── results/
    ├── example_report.md
    └── example_metrics.json

🧪 2. Lista funkcjonalna – co benchmarki muszą mierzyć
2.1 Metryki jakości
Metryka	Opis
HitRate@k	Czy właściwa pamięć znajduje się w top-k
MRR	Średnia odwrotnej pozycji trafienia
Precision@k	Dokładność odpowiedzi
Recall@k	Pokrycie źródeł
Semantic Similarity Score	Jakość embedderów
2.2 Metryki wydajności

Latencja średnia

Latencja P95 / P99

Throughput (zapytania/sekundę)

Czas dodania wpisów do pamięci

Koszt tokenów (jeśli używany LLM)

2.3 Metryki wewnętrzne RAE

Wpływ refleksji na jakość pamięci

Wpływ pruning/summarization

Wpływ GraphRAG

Wpływ różnych konfiguracji top_k

🔧 3. Minimalne wymagania do poziomu 6/5

To jest najważniejsza sekcja – implementujesz ją 1:1.

✔ 3.1. Dodanie 3 oficjalnych benchmark sets

Dodaj w katalogu benchmarking/sets/:

academic_lite.yaml

→ szybki test w <10 sekund
→ 3 memories, 5 queries
→ dla małych maszyn

academic_extended.yaml

→ 25–50 memories
→ 20 queries
→ odporność na szum i podobne pojęcia

industrial_small.yaml

→ 100–300 memories
→ prawdziwe „brudne dane”
→ test GraphRAG i refleksji

✔ 3.2. Oficjalny skrypt do uruchamiania benchmarków

benchmarking/scripts/run_benchmark.py:

ładuje YAML

wykonuje memories → insert

queries → search

zbiera metryki

zapisuje metrics.json i report.md

Polecenie:

python benchmarking/scripts/run_benchmark.py --set academic_lite.yaml

✔ 3.3. Compare engine

compare_runs.py – porównuje dwa wyniki:

python compare_runs.py runA.json runB.json


Wyniki:

różnice w MRR

różnice w jakości

różnice w latencji

wykresy (opcjonalnie)

✔ 3.4. Makefile targets

Dodaj:

benchmark-lite:
	.venv/bin/python benchmarking/scripts/run_benchmark.py --set academic_lite.yaml

benchmark-full:
	.venv/bin/python benchmarking/scripts/run_benchmark.py --set academic_extended.yaml

benchmark-industrial:
	.venv/bin/python benchmarking/scripts/run_benchmark.py --set industrial_small.yaml

✔ 3.5. Integracja z CI/CD

W pliku workflow:

dodaj job benchmark-smoke odpalany przy pull requestach

limit czasu: 60 sekund

tylko academic_lite.yaml

Efekt:
PR nie przejdzie, jeśli benchmark się pogorszył.

✔ 3.6. Dashboard integracja

W dashboardzie (opcjonalne po wdrożeniu):

sekcja „Benchmark Results”

tabelka z ostatnimi wynikami

wykres trendu MRR i latencji

📈 4. Jak wygląda benchmark klasy 6/5

Przykład raportu, który wygląda jak z laboratorium AGH / Google Research:

RAE Benchmark Report (ACADEMIC EXTENDED)
Machine: Intel i7, 16GB RAM
Config: RAE Lite, Reflection Engine ON

Dataset: 50 memories, 20 queries
Run time: 1.94 sec

Quality:
- HitRate@5: 0.84
- MRR: 0.71
- Semantic Precision: 0.88

Performance:
- Avg Latency: 44ms
- P95 Latency: 79ms
- Insert Time: 0.12s

Observations:
- Reflection improves MRR by +0.06
- GraphRAG improves entity alignment


To jest standard, który każdy naukowiec rozumie, a firma widzi od razu:

„To jest produkt przemyślany.”

📜 5. Checklista do zrobienia (w kolejności)
Faza 1 – struktura

 Utworzyć katalog benchmarking/sets/

 Dodać 3 zestawy YAML

 Dodać skrypt run_benchmark.py

 Dodać compare_runs.py

 Dodać BENCHMARK_STARTER.md i BENCHMARK_REPORT_TEMPLATE.md

Faza 2 – automatyzacja

 Dodać targety w Makefile

 Dodać job benchmark-smoke do GitHub Actions

 Dodać minimalny wynik w badge w README

Faza 3 – „wow factor”

 Dodać do dashboardu sekcję „Benchmark Results”

 Dodać kolorowe wykresy (lite)

 Przygotować example_report.md z wynikiem referencyjnym

Po wdrożeniu wszystkich punktów:

🎉 Benchmarking Suite w RAE osiąga poziom 6/5
To poziom projektów klasy Google Research, Meta FAIR, Anthropic evals.

🏁 6. Gotowy komunikat do repo

W README możesz dopisać ten blok:

### 🔬 Academic & Enterprise Benchmarking Suite
RAE includes a fully structured benchmarking environment:

- 3 official benchmark datasets (lite, academic, industrial)
- Automated scripts to run and compare results
- GitHub Actions benchmarking smoke tests
- Research-grade evaluation metrics (MRR, HitRate@k, latency, semantic precision)
- Report templates for university labs

See: /benchmarking/IMPROVEMENT_BENCHMARK_PLAN.md