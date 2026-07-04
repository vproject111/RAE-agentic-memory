# RAE TESTING KIT
Pakiet przygotowujący do uruchomienia testów i benchmarków dla RAE (Reflective Agentic-memory Engine)

Ten dokument opisuje:

1. Minimalne wymagania sprzętowe i programowe
2. Uruchomienie środowiska testowego (RAE Lite / Standard)
3. Instalację zależności Python
4. Uruchamianie testów jednostkowych, integracyjnych i wydajnościowych
5. Korzystanie z Evaluation Suite (`eval/`)
6. Jak przygotować się do benchmarków naukowych
7. Jak raportować wyniki

Dokument przeznaczony jest dla:
- zespołów badawczych (uczelnia, laboratoria AI)
- działów R&D firm
- inżynierów, DevOps i programistów
- niezależnych testerów

---

# 1. Wymagania

## 1.1 Sprzęt
**Konfiguracja minimalna (RAE Lite):**
- CPU: 4 wątki
- RAM: 8 GB
- Dysk: 5–10 GB

**Konfiguracja rekomendowana (RAE Standard / benchmarki):**
- CPU: 8–16 wątków
- RAM: 16–32 GB
- Dysk: 20–50 GB

## 1.2 Oprogramowanie
- Python 3.11+
- Docker + Docker Compose
- Git
- Make (zalecane)

---

# 2. Przygotowanie repozytorium

```bash
git clone https://github.com/dreamsoft-pro/RAE-agentic-memory
cd RAE-agentic-memory
git checkout main
```

Zaleca się wykonanie:

```bash
git pull origin main
```

aby upewnić się, że testy będą zgodne z najnowszą wersją kodu.

---

# 3. Uruchomienie środowiska (tryb Lite)

RAE Lite jest lekką konfiguracją dla małych maszyn, laptopów i środowisk testowych.

```bash
docker compose -f docker compose.lite.yml up -d
```

Po uruchomieniu sprawdź zdrowie API:

```bash
curl http://localhost:8000/health
```

Powinieneś otrzymać JSON typu:

```json
{ "status": "ok" }
```

---

# 4. Przygotowanie środowiska Python

## 4.1 Instalacja minimalna (testy lokalne)
```bash
make install
```

Instaluje:
- środowisko `.venv`
- dependencies z `requirements-dev.txt`
- SDK RAE (Tryb editable)

## 4.2 Instalacja pełna (dla uczelni / R&D)
```bash
make install-all
```

Instaluje dodatkowo:
- ML Service
- Reranker
- Evaluation Suite
- integracje (LangChain, LlamaIndex, MCP, Ollama wrapper itd.)

---

# 5. Uruchamianie testów

## 5.1 Testy jednostkowe (szybkie)
```bash
make test-unit
```

Zawiera testy:
- warstwy pamięci
- operacji bazodanowych
- zarządzania kontekstem
- API bez integracji LLM

Typowy czas wykonania: 15–45 sekund.

## 5.2 Pełne testy (cięższe)
```bash
make test
```

Obejmuje:
- integracje z ML Service
- testy wydajności
- testy kontraktów API
- testy komponentów ISO 42001

---

# 6. Evaluation Suite (eval/)

Evaluation Suite służy do wstępnej oceny:
- jakości retrievalu
- jakości pamięci semantycznej
- zgodności źródeł
- latencji zapytań
- odporności na szum

## 6.1 Uruchomienie

1. Upewnij się, że RAE Lite działa.
2. Zainstaluj zależności do eval:

```bash
pip install -r eval/requirements.txt
```

lub:

```bash
make install-all
```

3. Uruchom test:

```bash
.venv/bin/python eval/run_eval.py
```

## 6.2 Wyniki

Evaluation Suite zwraca:
- Hit Rate@5
- MRR (Mean Reciprocal Rank)
- Średnią latencję
- P95 latency
- Ścieżki źródeł pamięci

---

# 7. Benchmarki Systemowe i Naukowe

RAE posiada rozbudowany system benchmarków podzielony na trzy główne kategorie. Szczegółowe opisy znajdują się w `benchmarking/README.md`.

## 7.1 Zestawy Przemysłowe (Standard v1)
Testują system w scenariuszach rzeczywistych (RAG, biznes, messy data).

| Komenda | Zestaw | Opis |
|---------|--------|------|
| `make benchmark-lite` | `academic_lite` | Szybka walidacja poprawności matematycznej (<10s). |
| `make benchmark-extended` | `academic_extended` | Kompleksowa weryfikacja jakości odpowiedzi (~30s). |
| `make benchmark-industrial` | `industrial_small` | Mała skala danych rzeczywistych (~2min). |
| `make benchmark-large` | `industrial_large` | **SOTA Piotrek Baseline**: 1000+ pamięci, test kalibracji. |
| `make benchmark-drift` | `stress_memory_drift` | Test stabilności przy dryfcie wektorowym. |

## 7.2 Benchmarki Badawcze (Suite 9 of 5)
Zaawansowane testy izolacji i spójności logicznej AI.

- **LECT** (Logical Event Consistency): Czy system pamięta logiczną kolejność zdarzeń?
- **MMIT** (Multi-Memory Interference): Czy nowe fakty nie "nadpisują" starych błędnie?
- **GRDT** (Graph Reasoning Depth): Jak głęboko w grafie wiedzy system potrafi wnioskować?
- **RST** (Retrieval Stability): Czy wyniki są powtarzalne przy dużym szumie informacyjnym?
- **ORB** (Optimal Reasoning): Analiza Pareto: koszt vs jakość vs czas.

**Uruchomienie Bramki CI (Nine-Five):**
```bash
make benchmark-gate
```

## 7.3 Testy Ekstremalne (Skalowanie)
Dedykowane dla klastrów obliczeniowych (Node1/Node2).

- `industrial_extreme.yaml`: 10,000 pamięci.
- `industrial_ultra.yaml`: 100,000 pamięci (Wymaga Node1/Node2).

---

# 8. Raportowanie wyników

Każdy tester powinien użyć szablonu:

[BENCHMARK_REPORT_TEMPLATE.md](BENCHMARK_REPORT_TEMPLATE.md)

Zawiera on pola:
- konfiguracja testowa
- hardware
- wersja RAE
- przebieg testów
- metryki
- obserwacje

---

# 9. Checklista gotowości do testów

- [ ] RAE Lite uruchamia się i `/health` = ok
- [ ] `make install` lub `make install-all` bez błędów
- [ ] `make test-unit` przechodzi
- [ ] `eval/run_eval.py` zwraca wyniki
- [ ] katalog `benchmarking/` zawiera zestawy testowe
- [ ] tester ma dostęp do [BENCHMARK_REPORT_TEMPLATE.md](BENCHMARK_REPORT_TEMPLATE.md)

**RAE jest teraz gotowe do testów akademickich / R&D.**
