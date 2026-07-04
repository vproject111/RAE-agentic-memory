#RAE-OpenTelemetry-improvments-plan.md

1. Dla kogo to jest w praktyce?

Masz trzy grupy, którym OTel może służyć:

Naukowcy / badacze AI

chcą widzieć: jak agent myśli, które ścieżki wybiera, kiedy halucynuje, jak działa pamięć, jakie są koszty tokenowe.

Inżynierowie / SRE

interesuje ich: latency, błędy, throughput, problemy z Qdrant/Postgresem/LLM.

Ludzie od governance / zgodności

potrzebują: śladów decyzyjnych, dowodów na HIL, logiki polityk.

Jeżeli to zaprojektujesz dobrze, jedno OTel-instrumentation obsłuży wszystkie trzy światy, a różnicę zrobisz na poziomie eksporterów i konfiguracji.

2. Zasada kluczowa: „pełny sygnał w środku, różne widoki na zewnątrz”

Proponuję taki model:

W kodzie RAE (wewnątrz):

Zbierasz bogate, semantyczne sygnały, np.:

rae.agent.role (planner, evaluator, worker, router, …)

rae.memory.layer (episodic, semantic, reflective, graph)

rae.reasoning.step_type (decompose, retrieve, reflect, revise, decide)

rae.experiment.id (ID eksperymentu naukowego)

rae.llm.provider / rae.llm.model

rae.cost.tokens_input / rae.cost.tokens_output

rae.safety.intervention (czy guardrail zadziałał, jaki)

rae.outcome.label (success/fail/uncertain/needs_human)

To jest złoto dla naukowców, bo z tego można:

liczyć statystyki skuteczności per warstwa,

badać wpływ zmian architektury na koszt i jakość,

porównywać modele LLM na realnych zadaniach.

Na brzegu (eksporter / pipeline):

Tam tłumisz i filtrujesz w zależności od kontekstu:

środowisko dev/research: pełniejsze dane, eventy szczegółowe,

środowisko prod + medycyna/rząd:

sampling,

anonimizacja,

wycinanie wrażliwych pól,

krótsza retencja.

W praktyce:

kod RAE jest jeden,

różnią się tylko profile: config/otel_dev.yaml, config/otel_research.yaml, config/otel_prod_gov.yaml.

3. Co naukowcom naprawdę się przyda?

Jeżeli chcesz, żeby naukowiec spojrzał na RAE jak na platformę badawczą, daj mu te rzeczy:

Stabilne nazwy atrybutów

np. uchwalony „RAE Telemetry Schema v1”.

To ważniejsze niż idealna treść — liczy się powtarzalność.

Identyfikatory korelacji

rae.session.id

rae.task.id

rae.subtask.id
Bez tego analizy sekwencyjne i śledzenie całej ścieżki rozumowania są koszmarem.

Tagowanie eksperymentów

rae.experiment.id

rae.experiment.variant (A/B, model, konfiguracja pamięci)
To pozwala robić normalne badania: zmieniłeś coś → sprawdzasz różnicę na metrykach.

Metryki „naukowe”, nie tylko techniczne
Poza CPU, RAM i latency przyda się np.:

liczba kroków rozumowania,

liczba odwołań do pamięci,

rodzaj odpowiedzi (faktograficzna / generatywna / planująca),

wynik ewaluacji automatycznej (np. zgodność z etykietą, score od evaluator agenta).

4. A co z medycyną / rządem?

Tu możesz spokojnie:

nie eksportować treści promptów/odpowiedzi, tylko metadane:

długość promptu,

typ zadania,

kategorie (np. complaints/requests/info),

użyć PII scrubbera (Presidio lub własny),

stosować różne exportery:

naukowy → np. ClickHouse / Parquet do późniejszych analiz,

produkcyjny → Jaeger / Tempo / OTLP do SIEM/Splunk/Grafana.

Czyli:

naukowiec może dostać pełne, zanonimizowane dane o przebiegu pracy agentów,

regulator/zamawiający dostaje trace’y decyzyjne i metryki, ale bez wrażliwych treści.

To idealnie gra z ISO 42001 i z przyszłą zgodnością HIPAA/NIST.

5. Jak tego „nie popsuć” w architekturze?

Kilka prostych reguł:

Instrumentation w kodzie – cienkie, konsekwentne

nie mieszaj logiki biznesowej z tworzeniem spanów;

najlepiej mieć helpery typu rae_tracing.start_reasoning_step(...).

Brak twardych odwołań do konkretnego stacka (Grafana, Jaeger, itd.)

tylko standard OTel, eksportery wybierasz w konfiguracji.

Feature flagi / profile

RAE_TELEMETRY_PROFILE=research|prod|gov

w każdym profilu inny sampling, retencja, zestaw atrybutów.

Dokumentacja dla badaczy
Plik w repo typu:
docs/RAE-OpenTelemetry-Research-Guide.md:

opisuje, jakie są atrybuty,

jak łączyć dane,

przykładowe zapytania (SQL/PromQL).

Podsumowanie

To, że robisz OpenTelemetry „z myślą o naukowcach”, jest bardzo sensowne.

Klucz: bogate, ustandaryzowane atrybuty wewnątrz + różne profile eksportu na zewnątrz.

Dzięki temu:

naukowcy dostaną materiał do prawdziwych badań,

regulacje (medyczne, rządowe) nie będą problemem,

ISO 42001 dostaje twarde dane do governance.