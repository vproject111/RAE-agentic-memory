
---

```markdown
# REFLECTION_MODES.md
# Reflection Modes in RAE
## Stan faktyczny i warianty z LLM Orchestrator

Ten dokument opisuje:

1. Co robi **warstwa refleksji** w RAE niezależnie od LLM.
2. Jak refleksja działa w trzech trybach:
   - **bez LLM**,
   - z **pojedynczym LLM**,
   - z **wieloma LLM** via Orchestrator.
3. Jak to wpływa na adopcję w różnych branżach.

---

## 1. Co to jest „refleksja” w RAE

Refleksja w RAE ma dwa główne poziomy:

1. **Refleksja strukturalna (decyzyjna)**  
   - pracuje na:
     - czterech warstwach pamięci,
     - grafie powiązań,
     - funkcjach nagrody/kosztu (math),
     - metadanych epizodów.
   - decyduje o:
     - dekaju (przycinaniu, wygaszaniu),
     - łączeniu / dzieleniu wspomnień,
     - aktualizacji wag i priorytetów,
     - uruchamianiu określonych akcji (`reflect`, `prune`, `reindex`, itp.).

2. **Refleksja językowa (opisowa)**  
   - generuje:
     - ludzkie streszczenia („co się wydarzyło”),
     - tekstowe insighty („czego się nauczyliśmy”),
     - notatki dla użytkownika (raporty, podsumowania).
   - standardowo korzysta z **LLM** (przez LLM Orchestrator).

---

## 2. Tryb A – RAE bez LLM (`no-LLM mode`)

W tym trybie:

- **Brak podłączonego LLM** w Orchestratorze,
- albo wszystkie modele są ustawione jako `enabled=false`.

### 2.1. Co działa

- **Refleksja strukturalna**:
  - działa w pełni,
  - podejmuje decyzje o:
    - usuwaniu szumu z pamięci,
    - podnoszeniu/obniżaniu wag wspomnień,
    - aktualizacji grafu powiązań,
    - wyzwalaniu zadań w tle (np. przeliczenia metryk).
- **Warstwa math**:
  - liczy funkcje nagrody,
  - ocenia koszty,
  - może wykrywać wzorce w danych (np. progi, korelacje).
- **API pamięci**:
  - zapis/odczyt wspomnień,
  - zapytania po tagach, czasie, powiązaniach.

### 2.2. Co jest ograniczone

- **Brak tekstowych, „ładnych” podsumowań** generowanych przez LLM.
- Miejsca, które normalnie wołałyby LLM do tworzenia opisów:
  - mogą zwracać:
    - prostsze, techniczne opisy (np. listy ID wspomnień),
    - lub kontrolowany błąd „LLM niedostępny”.

### 2.3. Zastosowania

- **Administracja publiczna (JST)** – gdy nie wolno używać zewnętrznych LLM:
  - RAE służy jako pamięć instytucjonalna i silnik analityczny.
- **Przemysł** – śledzenie zdarzeń, decyzji, incydentów:
  - RAE trzyma historię i pozwala ją analizować bez generowania tekstu.
- **Badania naukowe nad pamięcią/MDP**:
  - pełne środowisko do testów bez kosztów LLM.

---

## 3. Tryb B – Refleksja z jednym LLM (`single-LLM mode`)

W tym trybie:

- LLM Orchestrator jest skonfigurowany w strategii `single`,
- wszystkie wywołania do LLM idą do jednego, wybranego modelu.

### 3.1. Co zyskujemy

- **Refleksja strukturalna**:
  - działa jak w trybie `no-LLM`.

- **Refleksja językowa**:
  - generuje:
    - streszczenia epizodów i sesji,
    - tekstowe insighty (np. „w ostatnich 7 dniach powtarzał się motyw X”),
    - opisowe raporty z warstwy math („te parametry rosną, te spadają”).

- **Użytkownik / system**:
  - dostaje czytelne, tekstowe „wnioski”, oparte na strukturze pamięci.

### 3.2. Ograniczenia

- Jesteśmy związani jednym modelem:
  - jego stylem,
  - jego mocnymi i słabymi stronami,
  - jego dostępnością.

Z punktu widzenia core to jednak jest **najprostszy tryb produkcyjny**, a Orchestrator umożliwia łatwe podmiany modelu bez zmian w RAE.

---

## 4. Tryb C – Refleksja z wieloma LLM (`multi-LLM via Orchestrator`)

W tym trybie:

- LLM Orchestrator ma skonfigurowane 2+ modele,
- strategie możliwe do użycia:
  - `single` (per zadanie wybierany jest inny model),
  - `fallback` (zapewnienie ciągłości),
  - `ensemble` (prosty multi-LLM).

### 4.1. Co zyskujemy

- **Elastyczność domenowa**:
  - inny model dla:
    - kodu,
    - prawa,
    - streszczeń,
    - tanich, prostych zadań.
- **Odporność na błędy / braki**:
  - fallback lokalny, gdy chmura zawiedzie,
  - możliwość eksperymentów z różnymi providerami bez przebudowy core.

- **Rozszerzona refleksja językowa**:
  - można:
    - porównać streszczenia z różnych modeli,
    - logować rozbieżności do warstwy refleksji,
    - z czasem budować „profil zaufania” do modeli w różnych kontekstach.

### 4.2. Co nadal jest opcjonalne

- Bardziej skomplikowane rzeczy typu:
  - debaty,
  - rywalizacja modeli,
  - negocjacje.

Te mechanizmy można wprowadzić **później**, na bazie tej samej architektury Orchestratora, jeśli pojawi się potrzeba naukowa lub biznesowa. Nie są wymagane, żeby RAE działał w praktyce.

---

## 5. Zależność refleksji od LLM – podsumowanie

Z punktu widzenia kodu i adopcji:

- **Refleksja strukturalna**:
  - działa **w każdym trybie** (no-LLM, single-LLM, multi-LLM),
  - jest częścią **core**,
  - odpowiada za faktyczne „zarządzanie pamięcią”.

- **Refleksja językowa**:
  - jest w pełni aktywna w trybach:
    - `single-LLM`,
    - `multi-LLM`,
  - w trybie `no-LLM`:
    - może być wyłączona,
    - lub zastąpiona prostymi opisami i raportami technicznymi.

To podejście:

- utrzymuje **spójny rdzeń matematyczno-strukturalny**,
- pozwala **rozsądnie skalować funkcje językowe** w zależności od środowiska.

---

## 6. Dlaczego to jest dobre dla adopcji

Takie rozdzielenie trybów refleksji:

1. **Nie obniża wartości projektu** – wręcz przeciwnie:
   - core pozostaje stabilny, niezależny od kaprysów dostawców modeli,
   - można go certyfikować / analizować / testować bez włączonego LLM.

2. **Ułatwia adopcję w różnych branżach**:
   - **JST / administracja**:
     - tryb `no-LLM` lub `single-LLM on-prem`,
     - spełnienie wymogów prawnych i bezpieczeństwa.
   - **Przemysł**:
     - możliwość połączenia z modelami lokalnymi lub chmurowymi,
     - kontrola kosztów przez Orchestrator.
   - **Nauka / R&D**:
     - badania nad pamięcią, MDP, multi-LLM,
     - możliwość łatwego podpinania kolejnych modeli do testów.

3. **Daje jasną historię inżynieryjną**:
   - RAE to przede wszystkim **silnik pamięci i refleksji strukturalnej**,
   - LLM to „warstwa komunikacyjna” i „opisowa”, **opCJOnalna** i w pełni pluggable.

---

## 7. TL;DR

- Refleksja *działa* bez LLM – wtedy jest bardziej „matematyczna i strukturalna”.
- LLM (jeden lub wiele) dodaje warstwę:
  - opisową,
  - narracyjną,
  - wygodną dla ludzi.
- LLM Orchestrator sprawia, że:
  - nie przyspawujesz się do jednego modelu,
  - łatwiej dopasujesz konfigurację do branży i środowiska.

Dzięki temu RAE może być:

- narzędziem dla naukowca,
- elementem infrastruktury w JST i przemyśle,
- platformą pod eksperymenty z multi-LLM,

bez konieczności przerabiania core przy każdej zmianie w świecie LLM.