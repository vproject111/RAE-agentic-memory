Zrobienie podkatalogów w docs/ zamiast zupełnie nowego katalogu na tym samym poziomie ma kilka korzyści:

zachowujesz jedną przestrzeń dokumentacji,

ale porządkujesz treści według celu,

a GitHub automatycznie wyświetli to czytelnie w strukturze docs/.

⭐ Rekomendowana struktura (propozycja profesjonalna)

Poniżej układ, który optymalnie rozdziela dokumentację formalną, projekty, eksperymenty i materiały AI:

docs/
│
├── reference/              # oficjalna dokumentacja projektu
│   ├── architecture/
│   ├── api/
│   ├── memory/
│   ├── iso-security/
│   ├── llm/
│   ├── deployment/
│   └── testing/
│
├── ai-specs/               # materiały do Claude/Gemini (briefy, specy, workflowy)
│   ├── generation/
│   ├── tests/
│   ├── evaluation/
│   └── agents/
│
├── project-design/         # notatki robocze, plany, koncepcje, eksperymenty
│   ├── rae-fold/
│   ├── rae-4layer-design/
│   ├── feniks-integration/
│   ├── enterprise-roadmap/
│   └── research-ideas/
│
└── guides/                 # przewodniki użytkownika
    ├── rae-lite/
    ├── small-business/
    ├── jst/
    └── developers/

🌟 Co daje taki podział?
1. Reference = oficjalna dokumentacja

Semantycznie „święte” miejsce — to jest to, czego używają użytkownicy i partnerzy, czyli:

Memory Model

GraphRAG

Reflection Engine V2

API

SDK

Deployment (Docker, Kubernetes)

Security & ISO 42001

LLM providers & Cost Guard

Testy & Coverage

To jest „produkcyjna” twarz projektu.

2. ai-specs = materiały robocze dla Claude/Gemini/Jules

Tutaj trafiają:

prompt-szablony

specyfikacje generowania testów

opisy tasków dla agentów

plany integracji LLM

workflowy obsługiwane przez Claude/Gemini

Czyli wszystko, czego nie powinno się mieszać z oficjalną dokumentacją — ale jest Ci potrzebne do pracy.

3. project-design = plany, koncepcje, R&D

To miejsce na:

RAE-Fold (notatki, modele, inspiracje biologiczne)

ewolucję architektury

rozważania o nowej warstwie pamięci

analizy porównawcze (GAM, własne podejścia, LlamaIndex/LangChain)

roadmapy

eksperymenty z agentami

Dzięki temu nie zaśmiecasz reference, ale nie tracisz też ważnych koncepcji.

4. guides = przewodniki użytkownika

To świetne miejsce na:

RAE Lite Guide

instrukcje dla JST

instrukcje dla małych firm

onboarding developerski

szybkie „how-to” dla SDK i CLI

To jest dokładnie to, czego potrzebuje Twój pilot w gminie i pierwszych klientów.

⭐ Dlaczego ta struktura jest optymalna?

Profesjonalnie wygląda (porządek enterprise).

Odróżnia dokumentację „kanoniczną” od notatek i eksperymentów.

Ułatwia skalowanie repo — nie skończy się bałaganem.

Łatwo prowadzić przeglądy (reference vs project-design).

Jest zgodna z praktyką dużych projektów open source.