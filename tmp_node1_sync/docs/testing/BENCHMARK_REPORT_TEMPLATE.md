# RAE Benchmark Report
Szablon raportu wyników testów

---

## 1. Informacje ogólne

**Tester:**
**Instytucja / firma:**
**Data:**
**Kontakt:**

---

## 2. Konfiguracja testów

- **Profil RAE:** Lite / Standard / Enterprise
- **Commit / Tag:**
- **Tryb uruchomienia:** Docker / Native
- **Użyty LLM (jeśli dotyczy):**
- **Embedder:**
- **Ustawienia top_k / max_tokens:**

---

## 3. Konfiguracja sprzętowa

- **CPU:**
- **RAM:**
- **Dysk:**
- **GPU (jeśli dotyczy):**

---

## 4. Zestaw benchmarkowy

- **Nazwa zestawu:**
- **Liczba wpisów pamięci:**
- **Liczba zapytań:**
- **Format:** YAML / JSON

---

## 5. Wyniki

### 5.1 Metryki jakości

- **HitRate@5:**
- **MRR:**
- **Accuracy:**
- **Overfetch / Underfetch cases:**

### 5.2 Wydajność

- **Średnia latencja (ms):**
- **P95 latencja (ms):**
- **Najwolniejsze zapytanie:**

### 5.3 Szczegółowe wyniki

| Query | Expected | Retrieved | Hit | Latency (ms) |
|-------|----------|-----------|-----|--------------|
|       |          |           |     |              |
|       |          |           |     |              |
|       |          |           |     |              |

---

## 6. Obserwacje

(Przestrzeń na komentarze testera)

- Czy system zachowywał się zgodnie z oczekiwaniami?
- Czy wystąpiły jakieś anomalie lub błędy?
- Jak system radził sobie z różnymi typami zapytań?
- Czy retrieval był stabilny i konsekwentny?

---

## 7. Wnioski / rekomendacje

(Np. "Silnik działa poprawnie dla małych datasetów, rekomenduję test na większym zbiorze", itp.)

---

## 8. Porównanie z baseline (opcjonalnie)

Jeśli przeprowadzono test A/B:

| Metrika | Wariant A | Wariant B | Delta |
|---------|-----------|-----------|-------|
| HitRate@5 | | | |
| MRR | | | |
| Avg Latency | | | |

---

## 9. Załączniki

- **Logi:**
- **Wyniki JSON:**
- **Pliki benchmarkowe:**
- **Screenshoty (jeśli dotyczy):**

---

## 10. Podpis

**Osoba wykonująca test:**
**Data wypełnienia:**
**Podpis / potwierdzenie:**

---

## Instrukcje wypełniania

1. Wypełnij wszystkie sekcje tak szczegółowo, jak to możliwe
2. Dołącz pliki JSON z wynikami (jeśli dostępne)
3. Dokumentuj wszelkie anomalie lub problemy
4. Zachowaj obiektywność w obserwacjach
5. Dodaj rekomendacje dla przyszłych testów

Ten szablon można zapisać jako:
- `reports/benchmark_YYYY-MM-DD_[nazwa].md`
- `results/[instytucja]_benchmark_report.md`

W razie pytań, skontaktuj się z zespołem RAE:
- GitHub: https://github.com/dreamsoft-pro/RAE-agentic-memory
- Issues: https://github.com/dreamsoft-pro/RAE-agentic-memory/issues
