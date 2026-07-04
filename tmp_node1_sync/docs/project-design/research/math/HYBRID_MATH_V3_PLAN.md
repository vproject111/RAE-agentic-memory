HYBRID_MATH_V3_PLAN.md
RAE – Hybrid Math v3

Minimalny, bezpieczny i sensowny plan modernizacji warstwy matematycznej
Cel: zwiększyć inteligencję modułu pamięci bez ryzyka destabilizacji silnika.

1. Filozofia projektowa

Hybrid Math v3 łączy:

Heurystyczną stabilność (Math v2 – relevance, importance, recency).

Nowe strategie (graph centrality, diversity, semantic density).

Uczony re-ranking (opcjonalny, lekki model ML).

Feedback z rzeczywistych zadań (learning-to-remember).

Całość jest podzielona na 3 iteracje, z pełnym bezpieczeństwem działania:

Każda iteracja działa jako nadbudowa, nie zamiennik.

System zawsze posiada fallback do Math v2.

Performance i koszt są kontrolowane na każdym etapie.

ITERACJA 1 — „Soft Hybrid” (strategiczne rozszerzenie bez ML)

Status: Zero ryzyka.
Cel: dodać kilka niezależnych strategii scoringu, zachowując deterministyczny pipeline.

1.1. Nowe sub-score’y

Dodać obliczanie następujących wartości (dla każdego rekordu pamięci):

Sub-score	Opis	Cel
score_relevance	Jak bardzo treść pasuje do zapytania	Podstawa selekcji
score_importance	Waga „globalna” rekordu	Priorytety wiedzy
score_recency	Świeżość rekordu	Dynamiczne wygaszanie
score_graph_centrality	Centralność w grafie (np. PageRank, degree)	Wiedza kluczowa strukturalnie
score_diversity	Penalizacja zbyt podobnych rekordów	Zwiększenie różnorodności kontekstu
score_density	Gęstość informacyjna (np. token count / semantyczna gęstość embeddingów)	Promowanie treści treściwych
1.2. Łączenie sub-score’ów

Wprowadzić funkcję:

hybrid_score = w1*relevance + w2*importance + w3*recency
              + w4*graph_centrality + w5*diversity + w6*density


Wagi w1–w6 są konfigurowalne per projekt/tenant.

Domyślne wartości = tak, aby zachować dominację relevance i importance.

1.3. Pipeline Iteracji 1

Filtrowanie twarde (np. relevance < threshold).

Obliczenie sub-score’ów.

Połączenie w jeden wynik hybrid_score.

Sortowanie i wybór np. TOP 50 kandydatów.

Zapis metryk i wykresów w OpenTelemetry.

1.4. Efekt

Większa trafność, różnorodność i odporność na duplikaty.

Nadal w pełni deterministyczne i przewidywalne.

Zero ryzyka dla silnika.

ITERACJA 2 — „Smart Re-Ranker” (uczona warstwa na małej puli)

Status: Niski koszt, bardzo duży zysk jakościowy.
Cel: dopracować ranking TOP-k za pomocą lekkiego modelu ML.

2.1. Zasada działania

Math v3 Iteracja 1 wybiera np. 30–50 najlepszych wspomnień.

Na tej małej puli uruchamiany jest Smart Re-Ranker (lekki model, np. MLP lub logistic regression).

Model wypluwa poprawiony ranking.

2.2. Feature’y wejściowe modelu

wszystkie sub-score’y z Iteracji 1,

wektor embeddingu rekordu (średni, skompresowany),

relacja semantyczna z query (cosine, dot-product),

cechy grafowe (centrality, cluster id),

recency bucket (np. one-hot: „bardzo świeże”, „średnie”, „stare”).

2.3. Wymagania bezpieczeństwa

Re-Ranker działa tylko, jeśli jest dostępny model.

if model_unavailable → fallback to hybrid_score.

Limit czasu np. 3–10 ms na re-ranking (mikro-model).

2.4. Pipeline Iteracji 2

Pipeline Iteracji 1 → TOP 50.

Re-Ranker → generuje nowy ranking.

Zwracamy np. TOP 8–12 do Working Memory.

2.5. Efekt

Poprawa trafności bez dużego kosztu obliczeniowego.

Możliwość adaptowania modeli per projekt (fine-tuning).

Silnik nadal w pełni stabilny.

ITERACJA 3 — „Feedback Loop” (learning-to-remember)

Status: Wyższy poziom – wejście w kierunku światowego SOTA.
Cel: system uczy się, które wspomnienia faktycznie pomogły w rozwiązaniu zadania.

3.1. Co zapisujemy podczas każdego requestu

które rekordy zostały wybrane do kontekstu,

czy były cytowane w odpowiedzi,

czy odpowiedź była poprawna / użyteczna / zaakceptowana,

czy klient zadał pytanie uzupełniające błędne → sygnał negatywny.

3.2. Aktualizacja wag (offline lub online)

Dla każdego rekordu:

if memory_helped:    importance += Δpos
if memory_hurt:      importance -= Δneg


Dodatkowo:

aktualizacja wag feature’ów w Re-Rankerze,

wzmacnianie klastrów grafowych, które są często cytowane.

3.3. Cele Iteracji 3

stworzyć model uczący się jak pamiętać,

automatycznie dostosowywać importance i hybrid_score,

poprawiać ranking w oparciu o rzeczywiste zachowania użytkowników.

3.4. Pipeline końcowy (Iteracje 1–3)
[Filtry twarde]
      ↓
[Heurystyki + sub-score’y → hybrid_score]
      ↓
[Smart Re-Ranker → adaptive ranking]
      ↓
[TOP-k pamięci do Working Memory]
      ↓
[Feedback zapisany do logów]
      ↓
[Lekki update importance / modelu]

3.5. Efekt

Dynamiczna ewolucja pamięci.

Jakość bliska SOTA (A-MEM / GAM / ReMe).

W pełni zgodne z RAE (bez przeprojektowywania architektury).

WYMAGANIA OGÓLNE I BEZPIECZEŃSTWA

Silnik pozostaje stabilny → każda iteracja musi mieć pełny fallback.

Procesy cięższe tylko na małej puli TOP-k (np. 30–50).

Konfigurowalne per tenant / projekt (różne profile: research / enterprise).

Pełna obserwowalność w OpenTelemetry:

osobne metryki dla źródeł score’ów,

heatmapy wpływu feature’ów,

statystyki poprawy odpowiedzi.

Backward compatibility → Math v2 może działać równolegle jako tryb „legacy safe”.