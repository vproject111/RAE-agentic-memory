# MATH_LAYER_CONTROLLER_DEVELOPMENT.md

## 1. Cel dokumentu

Celem tego dokumentu jest zaplanowanie rozwoju **algorytmu sterującego warstwą math** w RAE, przy założeniu, że:

- 3 poziomy warstwy math są już **zaimplementowane w kodzie** (to nie jest wizja, tylko stan faktyczny),
- 4-warstwowa pamięć (sensory / working / long-term / reflective) jest stabilnym fundamentem,
- benchmarki dla pamięci i warstwy math są opracowane **na poziomie przewyższającym** standardy OpenAI / DeepMind / Anthropic (wiele iteracji, porównanie do dostępnych benchmarków),
- testy CI (GitHub Actions) przechodzą – to jest **twarde kryterium bezpieczeństwa zmian**.

Ten dokument skupia się WYŁĄCZNIE na rozwoju **algorytmu sterującego** warstwą math – czyli tego, co:

- **decyduje, który poziom math** ma głos (1/2/3),
- **dobiera parametry** (progi, wagi, priorytety),
- **adaptuje się** na podstawie wyników i metryk.

## 2. Stan obecny – 3 poziomy warstwy math (skrót)

> Uwaga: nazwy modułów/funkcji należy dopasować do faktycznego kodu – poniżej jest opis poziomów, nie nazw plików.

Zakładamy, że w kodzie istnieją już:

1. **Math Level 1 – Deterministyczno-heurystyczny**
   - Zestaw reguł + scoring dla operacji pamięci (retrieve, prune, promote, decay).
   - Proste, zrozumiałe funkcje typu:
     - relevance score,
     - importance / criticality,
     - recency / decay,
     - koszt operacji (LLM / I/O / storage).
   - Decyzje podejmowane na podstawie **ustalonych formuł** i konfiguracji.

2. **Math Level 2 – Informacyjno-teoretyczny**
   - Kryteria typu:
     - entropia,
     - mutual information,
     - Information Bottleneck (maksymalizacja informacji przy ograniczonym „bottlenecku” kontekstu / pamięci).
   - Optymalizacja wyboru kontekstu i operacji na pamięci pod kątem:
     - jak najwięcej użytecznej informacji,
     - jak najmniej szumu / redundancji.

3. **Math Level 3 – Hybrydowy / adaptacyjny**
   - Mechanizmy uczące się / adaptacyjne:
     - np. bandyci (multi-armed bandits),
     - proste RL / meta-polityki decydujące:
       - kiedy korzystać z Level 1,
       - kiedy z Level 2,
       - kiedy z ich kombinacji.
   - Decyzje podejmowane na podstawie:
     - historii sukcesów danej strategii,
     - metryk z benchmarków i telemetry,
     - kontekstu zadania (typ zapytania, długość sesji, itd.).

**Założenie tego dokumentu:** te 3 poziomy są **zaimplementowane** i działają, ale algorytm sterujący (kiedy który poziom, jak dobrać parametry, jak uczyć politykę) może być rozwinięty i uporządkowany na poziomie „paper-grade”.

## 3. Cele rozwoju algorytmu sterującego warstwą math

1. **Stabilność i przewidywalność**
   - Brak „skakania” między strategiami w sposób chaotyczny.
   - Dobre defaulty w scenariuszach, gdzie mało danych historycznych.

2. **Wyjaśnialność (explainability)**
   - Możliwość odpowiedzi na pytanie:
     - *„Dlaczego kontroler wybrał tę strategię math w tym kroku?”*
   - Logi i ślady decyzyjne możliwe do analizy przez człowieka i przez refleksyjną warstwę pamięci.

3. **Wykorzystanie istniejących benchmarków**
   - Rozwój kontrolera **na bazie tego, co już jest**:
     - eksperymenty, które już masz,
     - metryki, które już są zdefiniowane.
   - Unikanie „benchmark-drift”: kontroler nie może zoptymalizować się tylko pod jeden typ testu.

4. **LLM-agnostyczność i kontrola kosztu**
   - Warstwa math ma wspierać:
     - działanie z jednym LLM,
     - konfiguracje z wieloma LLM (ensemble / rywalizacja / współpraca),
   - musi być świadoma kosztu:
     - nie zawsze używać „najdroższej strategii”.

5. **Gotowość do publikacji naukowej**
   - Algorytm sterujący opisany tak, żeby:
     - dało się go opisać formalnie,
     - dało się go zreplikować,
     - miał sens dla recenzenta z zewnątrz.

## 4. Docelowa architektura kontrolera warstwy math

### 4.1. High-level interfejs

Proponowany interfejs (przykładowy, dopasuj do faktycznych nazw):

```python
decision = math_layer_controller.decide(
    task_context=task_context,
    memory_state=memory_state_snapshot,
    metrics=recent_metrics,
    config=controller_config,
)
Gdzie decision zawiera m.in.:

selected_level: {1, 2, 3} lub kombinację (np. ["L1", "L2"]),

strategy_id: nazwa/ID konkretnej strategii w danym poziomie,

params: dobrane parametry (np. progi, wagi),

explanation: krótki tekst / struktura wyjaśniająca decyzję,

telemetry_tags: co warto zalogować dla analizy i uczenia.

4.2. Warstwy odpowiedzialności
Warstwa obserwacji (features)

Zbiera:

typ zadania,

cechy pamięci (liczba slotów, rozkład wag, entropia),

ostatnie wyniki benchmarków / lokalnych metryk,

budżet kosztowy (czas / pieniądze / tokeny),

informacje o LLM (latencja, błędy, itp.).

Warstwa wyboru polityki (policy selection)

Na podstawie obserwacji wybiera:

poziom math (1/2/3),

strategię w danym poziomie.

Może używać:

reguł (L1),

funkcji scoringowych (L2),

bandytów / RL (L3).

Warstwa parametrów

Dostraja parametry strategii:

wagi komponentów score,

progi IB,

limity długości kontekstu,

progi aktywacji refleksji.

Warstwa feedbacku / nauki

Na podstawie:

wyników benchmarków,

telemetry,

feedbacku z refleksyjnej warstwy pamięci,

aktualizuje:

preferencje polityk (np. wagi bandytów),

rekomendowane defaulty.

5. Plan rozwoju – 3 iteracje
Iteracja 1 – Uporządkowanie i ujednolicenie kontrolera
Cel: wyciągnąć istniejące 3 poziomy math pod jeden spójny kontroler, bez zmiany „matematyki w środku”.

Zadania:

Wyodrębnienie kontrolera

Upewnij się, że istnieje jeden główny moduł / klasa, np.:

math_layer_controller.py / MathLayerController.

Logika „który poziom wybrać i w jakiej konfiguracji” nie jest rozsiana po różnych plikach.

Jednolity format decyzji

Wprowadź jednolitą strukturę MathDecision (dataclass / pydantic), zawierającą:

selected_level,

strategy_id,

params,

explanation,

telemetry_tags.

Konfiguracja kontrolera

Plik konfiguracyjny, np. config/math_controller.yaml:

domyślne progi i wagi,

opcje włącz/wyłącz dany poziom,

profile (np. research_mode, production_mode, cheap_mode).

Logging i telemetry

Dodaj spójne logowanie:

każde wywołanie kontrolera zapisuje decyzję + kluczowe features,

integracja z OpenTelemetry/metrykami, które już masz.

Testy

Testy jednostkowe:

czy kontroler zawsze zwraca poprawną strukturę decyzji,

czy reaguje poprawnie na ekstremalne konfiguracje.

Testy integracyjne:

czy pamięć działa poprawnie, gdy kontroler wybiera różne poziomy math.

Definition of Done:

Istnieje jeden główny punkt wejścia dla sterowania math layer.

Decyzje są logowane w ustandaryzowany sposób.

CI przechodzi, benchmarki nie są gorsze niż przed zmianami.

Iteracja 2 – Data-driven policy (uczenie na logach i benchmarkach)
Cel: wykorzystać istniejące logi + benchmarki do wstępnego wyuczenia polityki kontrolera, nadal głównie offline.

Zadania:

Kolekcja danych

Zbierz logi z:

decyzjami kontrolera,

wynikami benchmarków,

metrykami jakości / kosztu.

Ustal format datasetu (np. eval/math_policy_logs/).

Definicja funkcji nagrody

Zdefiniuj funkcję reward(decision, outcome):

uwzględnia:

jakość odpowiedzi,

stabilność pamięci,

koszt (tokeny, czas),

ewentualne kary za „katastrofalne błędy”.

Analiza offline

Zidentyfikuj:

w jakich scenariuszach Level 1/2/3 radził sobie najlepiej,

gdzie kontroler mógł wybrać lepiej,

typowe wzorce (np. długie zadania → L2+L3, krótkie → L1).

Policy heuristics v2

Na podstawie analizy:

doprecyzuj reguły wyboru poziomu (nadal deterministyczne, ale mądrzejsze),

zdefiniuj proste „policy rules” oparte na features (np. liczba turns, entropia pamięci, typ benchmarku).

Ablation studies

Porównaj:

stary kontroler vs nowy policy v2,

Level 1 only vs 1+2 vs 1+2+3,

na istniejących benchmarkach.

Definition of Done:

Mamy opisane i zaimplementowane policy v2:

lepiej wykorzystuje 3 poziomy math,

ma formalnie zdefiniowaną funkcję nagrody,

poprawia wyniki przynajmniej w części scenariuszy bez regresu w kluczowych.

Iteracja 3 – Online adaptacja (bandyci / proste RL)
Cel: wprowadzić adaptacyjny kontroler, który uczy się w trakcie pracy, ale z mocnymi bezpiecznikami.

Zadania:

Wybór mechanizmu

Postaw na:

multi-armed bandits jako pierwszy krok (prostsze niż pełne RL),

ramię = kombinacja (poziom math, strategia, konfiguracja).

Definiujesz eksplorację/eksploatację (np. ε-greedy / UCB).

Integracja z istniejącą polityką

Bandyta działa nad policy v2:

policy v2 proponuje „baseline” decyzję,

bandyta może czasem wybrać inny wariant do eksploracji.

Bezpieczniki

Twarde ograniczenia:

max odsetek eksperymentalnych decyzji,

brak eksperymentów w trybach „production/strict”.

Detekcja degradacji:

jeśli średni reward spada poniżej progu → rollback do baseline.

Aktualizacja polityki

Na podstawie wyników bandyty:

aktualizujesz wagi w konfiguracji kontrolera,

zapisujesz „insights” do refleksyjnej warstwy pamięci:

jakie konfiguracje działają najlepiej w jakich scenariuszach.

Eval i raport

Uruchom pełne benchmarki:

baseline (policy v2, bez bandytów),

policy v2 + bandyci.

Przygotuj raport:

gdzie adaptacja daje zysk,

gdzie musi być wyłączona.

Definition of Done:

Kontroler potrafi adaptować się online (w trybach research / lab),

W trybach produkcyjnych zachowuje się przewidywalnie (baseline policy),

Mamy dowód (benchmark + raport), że adaptacja daje wymierne korzyści.

6. Rola „mądrzejszego” modelu LLM w rozwoju warstwy math
Na potrzeby rozwoju kontrolera math zalecany jest hybrydowy tryb pracy z modelami:

Mocniejszy model – tylko do „ciężkiego myślenia”

Sesje, w których:

projektujesz nowe warianty policy,

analizujesz logi i wyniki benchmarków,

szukasz nietrywialnych heurystyk i insightów.

Typowe zadania:

„przeczytaj ten raport z evali i zaproponuj 3 konkretne zmiany w policy”,

„zaprojektuj funkcję nagrody i uzasadnij jej kształt”.

Średni model – do implementacji i utrzymania

Refaktory, dopisywanie testów,

wdrażanie decyzji wypracowanych z mocniejszym modelem,

iteracyjne poprawki kodu kontrolera.

Bezpieczeństwo przez testy

Każda zmiana w kontrolerze MUST:

przechodzić istniejące testy,

być objęta nowymi testami, jeśli zmienia zachowanie.

7. Kryteria „gotowości naukowej” algorytmu sterującego
Na potrzeby publikacji naukowej algorytm sterujący warstwą math będzie uznany za „paper-ready”, gdy:

Formalizacja

Są formalnie zdefiniowane:

przestrzeń stanów (features kontrolera),

przestrzeń akcji (strategie / konfiguracje),

funkcja nagrody.

Opis algorytmów

Dokładny opis:

policy v1 (obecna),

policy v2 (data-driven),

policy v3 (online adaptacja – bandyci / RL).

Eksperymenty

Wyniki na zewnętrznych / własnych benchmarkach:

porównanie wariantów,

analizy ablation,

trade-off koszt/jakość.

Replikowalność

Skrypty w benchmarking/ pozwalają:

uruchomić każdy wariant kontrolera,

zreplikować wyniki (przynajmniej zbliżone).

8. Następne kroki
Zaimplementuj Iterację 1:

wyodrębnienie MathLayerController,

ujednolicenie formatu decyzji,

logging + testy.

Po zrobieniu Iteracji 1:

uruchom pełne benchmarki,

zapisz wyniki jako baseline dla Iteracji 2.

Gdy Iteracja 1 będzie stabilna:

przejdź do Iteracji 2 (policy v2 oparta na danych z logów),

z udziałem mocniejszego modelu LLM do analizy benchmarków i projektowania heurystyk.

Iteracja 3:

dopiero gdy policy v2 jest dobrze zrozumiana i opisana,

wprowadzaj bandytów / RL z mocnymi bezpiecznikami.