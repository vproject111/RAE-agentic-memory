#RAE-v-TITAN-form-google
popatrz co znalazłem w nowościch google:

Google wprowadziło architekturę
Titans oraz framework MIRAS, które stanowią znaczący postęp w stosunku do tradycyjnych modeli Transformer. Te innowacje mają na celu rozwiązanie problemów związanych z obsługą długiego kontekstu i wydajnością obliczeniową, z którymi borykają się starsze architektury. 
Główne nowości to:

    Architektura Titans: Jest to nowa architektura inspirowana neurobiologią, która wprowadza mechanizmy pamięci krótko- i długoterminowej, a nawet zdolność do "zapominania" mniej istotnych informacji.
    Framework MIRAS (Memorization, Information Retrieval, and Associative Systems): Stanowi on teoretyczne ramy dla architektury Titans, umożliwiając modelom AI szybszą pracę i obsługę znacznie większych kontekstów poprzez aktualizację ich pamięci podczas działania.
    Lepsza obsługa długiego kontekstu: Poprzednie modele Transformer miały ograniczenia w skalowaniu do bardzo długich sekwencji (np. przetwarzanie całych dokumentów) ze względu na wysokie koszty obliczeniowe. Titans + MIRAS rozwiązują ten problem, umożliwiając efektywne wykorzystanie obszernej pamięci historycznej.
    Zwiększona wydajność: Nowa architektura pozwala na znacznie szybsze działanie modeli AI i może być szkolona równolegle, co przyspiesza badania i zmniejsza zapotrzebowanie na zasoby obliczeniowe.
    Wprowadzenie modelu FunctionGemma: Google wydało również FunctionGemma, mały model (270 milionów parametrów) przeznaczony do działania na urządzeniach brzegowych (lokalnie na telefonach, przeglądarkach, urządzeniach IoT) bez połączenia z chmurą. Model ten specjalizuje się w tłumaczeniu poleceń języka naturalnego na ustrukturyzowany kod. 

Te przełomowe rozwiązania mają potencjał do przyspieszenia rozwoju sztucznej inteligencji ogólnej (AGI) i stanowią znaczący krok naprzód od momentu wprowadzenia oryginalnej architektury Transformer w 2017 roku. 

To co wkleiłeś jest w dużej mierze zgodne z tym, co Google opisało publicznie — tylko w Twoim streszczeniu są 2 miejsca, gdzie łatwo „dopalić marketing” bardziej niż wynika z materiałów.

Co to jest Titans i MIRAS naprawdę (bez nadęcia)

Titans to rodzina architektur, która dokłada do „krótkiej pamięci” attention (czyli kontekstu w oknie) osobny moduł pamięci długoterminowej, który potrafi zapamiętywać podczas działania (test-time memorization) i pomagać modelowi korzystać z informacji sprzed bardzo dawna — bez płacenia pełnej ceny kwadratowej uwagi na całej historii. 
arXiv
+2
arXiv
+2

MIRAS to nie „kolejny model”, tylko ramy projektowe: patrzy na Transformery, Titans i nowoczesne (liniowe) RNN/SSM jak na odmiany pamięci asocjacyjnej, a potem mówi: „taki model da się opisać czterema pokrętłami”:

architektura pamięci, 2) attentional bias (cel/strata sterująca aktualizacją), 3) retention/forget gate, 4) algorytm uczenia pamięci (online optimization). 
arXiv
+1

W samym MIRAS autorzy pokazują też konkretne instancje (Moneta/Yaad/Memora) wynikające z tych wyborów. 
arXiv
+1

Co jest nowe vs Transformer

Transformer ma świetną „pamięć krótką” (dokładne zależności w bieżącym oknie), ale koszt uwagi rośnie źle dla bardzo długich sekwencji.

Titans dodaje moduł, który ma pełnić rolę pamięci długiej i być aktualizowany w czasie użycia, dzięki czemu model może lepiej korzystać z bardzo odległej przeszłości. 
arXiv
+1

MIRAS próbuje to uporządkować teoretycznie i projektowo (żeby nie było „tuningowania na czuja”). 
arXiv
+1

Dwie ważne korekty do Twojego streszczenia

„Przyspiesza AGI” – to jest spekulacja publicystyczna. W materiałach Google jest narracja o długiej pamięci i efektywności, ale „krok do AGI” to już interpretacja. 
Google Research

„Znacznie szybsze zawsze” – wyniki są obiecujące, ale istnieją też krytyczne reimplementacje, które pokazują, że przewagi zależą od detali (np. chunking) i nie zawsze wygrywa „na wszystkim”. 
arXiv

FunctionGemma – co to jest i do czego (praktycznie)

FunctionGemma to mały model ~270M, dostrojony do function calling: ma tłumaczyć polecenia NL → ustrukturyzowane wywołania narzędzi/API (czyli dokładnie warstwa „tool router / action compiler” dla agentów, także lokalnie/edge). 
blog.google
+2
Google AI for Developers
+2

Co z tego wynika dla RAE (konkretnie)

Titans/MIRAS to „pamięć w modelu” (parametryczna / modułowa), a RAE to „pamięć obok modelu” (zewnętrzna, audytowalna, provider-agnostic). To się nie gryzie – to się składa.

Jeśli kiedyś będziesz chciał mieć „local-first agent” naprawdę autonomiczny, to FunctionGemma wygląda jak sensowny kandydat na lokalny moduł: NL → tool call (np. MCP tool invocation), a RAE robi politykę, pamięć, kontekst, kontrolę kosztu i audyt.

MIRAS daje Ci fajny język do README/whitepapera RAE: możesz jasno odróżnić retencję/forgetting w pamięci zewnętrznej (RAE) od retencji w architekturze modelu (Titans/MIRAS).

Jeśli chcesz, podeślij 1–2 akapity, które planujesz dopisać do README RAE na bazie tej nowinki — przerobię to na wersję „bez marketingu”, ale z mocną wartością poznawczą i bez ryzykownych twierdzeń.

w pierwszej chwili miałem wrażenie, że to jakby kopia tego co robię, ale widzę, że nie:-)
Jak to z sensem opisać w readme? najpierw krótko w wyjaśnić w rozwinięciu

Pewnie. Najlepszy „sensowny” opis w README to taki, który:

nie brzmi jak reakcja na newsy, tylko jak świadome pozycjonowanie,

jasno rozdziela pamięć w architekturze modelu vs pamięć systemową / zewnętrzną,

pokazuje, że RAE nie konkuruje z Titans/MIRAS, tylko jest „warstwą nad” i „obok”.

Poniżej masz gotowce: krótko (do README) + rozwinięcie (sekcja “Related Work / Context”).

Krótko do README (2–4 zdania)
### How RAE relates to "long-context / memory" model architectures
Recent research explores adding *internal* long-term memory to model architectures (e.g., memory-augmented Transformers).  
RAE focuses on *external, system-level memory*: auditable, provider-agnostic, privacy-first storage + retrieval + policies, usable with any LLM (local or cloud).  
These approaches are complementary: internal memory can improve a model’s reasoning within a run, while RAE provides durable memory, governance, and repeatable workflows across sessions, tools, and environments.


Jeśli chcesz jeszcze krócej:

RAE is external, auditable memory for agents (model-agnostic).  
Memory-augmented model architectures are internal memory inside the model.  
They complement each other.

Rozwinięcie do README (sekcja “Context / Related Work”)
## Context: internal model memory vs external agent memory

There are two different meanings of "AI memory":

1) **Internal memory (model architecture)**  
   Some architectures add mechanisms for long-term / online memorization and forgetting inside the model itself.
   Goal: better long-context handling and efficient use of historical information *within* the model’s forward pass.

2) **External memory (system architecture) — RAE**  
   RAE is a memory engine *outside* the model:
   - durable storage (episodic/semantic/reflective layers),
   - retrieval + ranking + policies (privacy / cost / access control),
   - auditability and reproducibility across sessions,
   - provider-agnostic connectors (LLMs, vector DBs, SQL, caches).

### Why RAE is different
Even if a model gains powerful internal memory, real systems still need:
- **governance** (what can be stored, for how long, and who can access it),
- **auditability** (why a decision was made, which sources were used),
- **portability** (switch models/providers without losing memory),
- **tooling integration** (email, DB, files, MCP tools, CI, etc.).

### How they can work together
RAE can optionally plug in:
- local "tool-routing" models (NL → structured tool calls),
- memory-augmented LLMs as providers,
- policies that decide *what* gets written to external memory vs kept ephemeral.

In short:
- **internal memory** improves model capability in a run,
- **RAE external memory** makes an agent reliable, repeatable, and governable over time.

Mini-diagram (czytelny i działa w README)
LLM (any provider) ── reasoning ──┐
                                 │
                          RAE Memory Layer
                                 │
Tools / MCP / DB / Files ────────┘


Albo wersja „internal vs external”:

Internal memory (inside model)  ≠  External memory (RAE)
"better long context"              "durable, auditable, governed memory"

Gdzie to wstawić w README

Jeśli README ma być krótkie: wrzuć krótką wersję do sekcji “What is RAE?” lub “FAQ”.

Jeśli masz dłuższy dokument architektury: wrzuć rozwinięcie do docs/CONTEXT.md i w README daj 2–3 zdania + link.