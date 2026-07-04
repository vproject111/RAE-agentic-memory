✅ 3) MATH_EXPERIMENTS_PLAN.md

Plik: experiments/MATH_EXPERIMENTS_PLAN.md

📘 RAE Math Layer – Experimental Research Plan
Research-grade experiments for validating the mathematical model of agent memory.
🎯 Cel eksperymentów

Celem eksperymentów jest:

potwierdzenie naukowe 3-warstwowego modelu matematycznego pamięci,

analiza stabilności i jakości pamięci RAE,

stworzenie podstaw do publikacji naukowych,

porównanie różnych polityk pamięci.

🧪 1. Eksperyment: Structural Stability Test
Procedura:

Wczytaj dataset industrial_small.

Wstaw wszystkie wspomnienia.

Zmierz:

Graph Connectivity

Entropy

Semantic Coherence

Dodaj 20% nowych wspomnień.

Powtórz pomiary.

Oczekiwany wynik:

umiarkowany wzrost GCS,

niska zmiana entropii,

wzrost spójności semantycznej.

🔄 2. Eksperyment: Drift Dynamics Test
Procedura:

Zapisz snapshot t0.

Uruchom 100 zapytań i refleksji.

Zapisz snapshot t1.

Policz:

MDI,

structural drift,

retention curve.

Oczekiwany wynik:

niski drift,

zachowana spójność struktury.

🔁 3. Eksperyment: Reflection Gain Analysis
Procedura:

Zadaj 30 pytań bez refleksji.

Zmierz baseline MRR.

Uruchom refleksję.

Powtórz pytania.

Metryki:

Reflection Gain (RG),

koszt refleksji (tokens),

Cost–Quality Frontier.

🛡️ 4. Eksperyment: Robustness & Poisoning
Procedura:

Wczytaj dataset z konfliktem (poisoned).

Mierz poprawność odpowiedzi i RG po refleksji.

Porównaj z datasetem czystym.

Wynik:

odporność na konflikty,

zdolność do autokorekty.

⚖️ 5. Eksperyment: Memory Policy Optimization

Porównanie trzech trybów:

policy = light_reflection
policy = deep_reflection
policy = hybrid_reflection


Mierzymy:

jakość odpowiedzi,

drift,

koszt operacji.

📉 6. Eksperyment: Entropy Minimization

Sprawdzamy, czy RAE w naturalny sposób dąży do obniżania entropii pamięci poprzez:

integrację,

uogólnienie,

refleksję,

konsolidację grafu.

🧩 7. Eksperymenty porównawcze z baseline

Dla RAG, RAE-no-reflection, pełnego RAE:

porównujemy wszystkie matematyczne metryki

wykresy:

drift vs czas,

retention curve,

RG gain,

entropia vs czas.

KONIEC PLIKU