# BENCHMARK STARTER
Zestawy startowe do testów jakości i wydajności RAE

Ten dokument zawiera:

- opis minimalnych benchmarków
- format danych wejściowych
- przykładowe zestawy goldenset
- sposób uruchamiania benchmarków
- jak definiować zestawy A/B

---

# 1. Struktura benchmarków

Benchmark składa się z:

1. **memories:**
   Zestaw wpisów, które trafiają do pamięci przed testem.

2. **queries:**
   Lista zapytań do silnika pamięci.

3. **expected:**
   Oczekiwane ID lub tagi, które powinien zwrócić retriever.

---

# 2. Format danych (YAML)

```yaml
memories:
  - id: "m1"
    text: "Albert Einstein was a theoretical physicist."
    tags: ["physics", "einstein"]

  - id: "m2"
    text: "Marie Curie discovered radium."
    tags: ["chemistry", "curie"]

queries:
  - query: "Who was Einstein?"
    expected_source_ids: ["m1"]

  - query: "What did Marie Curie discover?"
    expected_source_ids: ["m2"]
```

---

# 3. Przykładowy Benchmark: Academic Lite

Folder: `benchmarking/academic_lite.yaml`

```yaml
memories:
  - id: "1"
    text: "DNA was discovered by Watson and Crick."
    tags: ["biology", "dna"]

  - id: "2"
    text: "The capital of France is Paris."
    tags: ["geography"]

  - id: "3"
    text: "Python is a popular programming language."
    tags: ["technology"]

queries:
  - query: "What is the capital of France?"
    expected_source_ids: ["2"]

  - query: "Who discovered DNA?"
    expected_source_ids: ["1"]
```

---

# 4. Uruchamianie benchmarków

```bash
.venv/bin/python eval/run_eval.py --benchmark benchmarking/academic_lite.yaml
```

---

# 5. Benchmark A/B

Możesz porównywać:
- różne strategie pamięci
- różne modele LLM
- różne wartości `top_k`
- różne embeddery

Przykład:

```bash
# Wariant A – standard config
RaeMemory --config configs/memory_standard.yaml

# Wariant B – agresywny pruning
RaeMemory --config configs/memory_pruning.yaml
```

Następnie oba wyniki opisujesz w [BENCHMARK_REPORT_TEMPLATE.md](BENCHMARK_REPORT_TEMPLATE.md).

---

# 6. Przykładowe zestawy danych

## 6.1 Small Dataset (10 memories, 5 queries)
Idealny do szybkiego smoke testu przed większymi eksperymentami.

## 6.2 Medium Dataset (100 memories, 25 queries)
Dla testów jakości retrievalu i rankingu.

## 6.3 Large Dataset (1000+ memories, 100+ queries)
Dla testów wydajności, latencji i skalowalności.

---

# 7. Metryki jakości

Evaluation Suite zwraca następujące metryki:

- **Hit Rate@K** – procent zapytań, które znalazły poprawny dokument w top-K wynikach
- **MRR (Mean Reciprocal Rank)** – średnia odwrotności pozycji pierwszego poprawnego wyniku
- **Precision@K** – precyzja w top-K wynikach
- **Recall@K** – recall w top-K wynikach
- **Latency** – średni czas odpowiedzi (ms)
- **P95 Latency** – 95. percentyl czasu odpowiedzi

---

# 8. Format wyników

Wyniki są zapisywane w formacie JSON:

```json
{
  "benchmark_name": "academic_lite",
  "timestamp": "2025-12-06T19:00:00Z",
  "config": {
    "top_k": 5,
    "embedder": "text-embedding-3-small",
    "reranker": "bge-reranker-base"
  },
  "metrics": {
    "hit_rate_at_5": 0.95,
    "mrr": 0.87,
    "avg_latency_ms": 124,
    "p95_latency_ms": 210
  },
  "queries": [
    {
      "query": "What is the capital of France?",
      "expected": ["2"],
      "retrieved": ["2", "5", "7"],
      "hit": true,
      "latency_ms": 98
    }
  ]
}
```

---

# 9. Tworzenie własnych benchmarków

1. Stwórz plik YAML w katalogu `benchmarking/`
2. Zdefiniuj `memories` i `queries`
3. Opcjonalnie dodaj `expected_source_ids` dla każdego query
4. Uruchom eval suite z flagą `--benchmark`
5. Zapisz wyniki w [BENCHMARK_REPORT_TEMPLATE.md](BENCHMARK_REPORT_TEMPLATE.md)

---

# 10. Best Practices

- **Używaj różnorodnych danych** – testuj na różnych domenach (technika, medycyna, prawo)
- **Testuj edge cases** – zapytania niejednoznaczne, z błędami, w różnych językach
- **Dokumentuj konfigurację** – zapisuj wszystkie parametry dla reprodukowalności
- **Porównuj z baseline** – zawsze miej punkt odniesienia (np. proste wyszukiwanie słów kluczowych)
- **Testuj na prawdziwych danych** – syntetyczne benchmarki są dobre na start, ale produkcyjne dane są kluczowe

---

# 11. Dostępne zestawy benchmarkowe

RAE dostarcza następujące gotowe zestawy:

- `academic_lite.yaml` – 10 faktów naukowych, 5 zapytań
- `multilingual_test.yaml` – testy wielojęzyczne (EN, PL, DE, FR)
- `noise_robustness.yaml` – zapytania z błędami ortograficznymi
- `temporal_test.yaml` – dane z datami i wydarzeniami historycznymi

Wszystkie znajdują się w katalogu `benchmarking/`.
