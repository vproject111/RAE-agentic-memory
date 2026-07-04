# PLAN REFAKTORU: IRON RAE (Math Layers Optimization)

## Cel Strategiczny
Osiągnięcie spektakularnych, powtarzalnych wyników benchmarków (LECT > 0.9999, GRDT > 0.8, MPEB > 0.95) poprzez wzmocnienie matematycznego rdzenia (Core), zachowując pełną agnostyczność modelu i przygotowując system pod implementację w Rust.

## Główne Założenia
1. **3 Warstwy MATH**: Pozostają jako fundament precyzji.
2. **4 Warstwy Pamięci**: Working, Episodic, Semantic, Reflective.
3. **Multi-Vector Support**: Brak "równania w dół" – obsługa wektorów o różnych długościach jednocześnie.
4. **OpenTelemetry**: Pełna w wersji Standard, wyłączona w wersji Lite.
5. **Model-Weak, Architecture-Strong**: System musi działać poprawnie nawet przy słabym modelu LLM.

## Fazy Realizacji

### Faza 1: MATH-2 – Fuzja Wielowymiarowa (Multi-Vector Fusion)
- **Problem**: Konieczność ujednolicania wymiarów wektorów (np. 384 vs 1536).
- **Rozwiązanie**: Implementacja **Late Fusion** przy użyciu algorytmu **RRF (Rank Reciprocal Fusion)**.
- **Działanie**: RAE przeszukuje wiele przestrzeni wektorowych równolegle i łączy wyniki na poziomie rankingów.
- **Status**: Do rozpoczęcia.

### Faza 2: MATH-1 – Deterministyczna Logika Topologiczna
- **Problem**: Halucynacje relacji w grafie przy słabszych modelach.
- **Rozwiązanie**: Wprowadzenie **GraphTopologyEngine**.
- **Działanie**: Dijkstra/BFS do matematycznego dowodzenia ścieżek w pamięci semantycznej. LLM pełni rolę wyłącznie opisową.
- **Status**: Zaplanowano.

### Faza 3: MATH-3 – Kontrola Dynamiki (Stability Governor)
- **Problem**: Niestabilność refleksji i dryfowanie metryk.
- **Rozwiązanie**: Implementacja **Kontrolera PID** oraz **Filtru Kalmana**.
- **Działanie**: Wygładzanie zmian ważności wspomnień, odfiltrowywanie szumu poznawczego modeli LLM.
- **Status**: Zaplanowano.

## Definition of Done
- Wszystkie benchmarki 9/5 przechodzą powyżej zdefiniowanych progów (Gate).
- System obsługuje jednocześnie modele OpenAI (1536-dim) i Ollama (384-dim).
- Logika matematyczna jest odseparowana od LLM (Pure Functions).
