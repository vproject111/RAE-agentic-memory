# TASK: Implement Memory Contract Validation at Startup (RAE)

## Context
RAE uses persistent memory (Postgres + vector DBs + telemetry storage).
Currently the system relies on:
- migrations generated over time
- implicit assumptions about database state

This is NOT sufficient.

We need an explicit, runtime-safe mechanism that:
- validates the actual database structure against an expected contract
- fails fast if memory is inconsistent
- does NOT silently auto-fix or guess

This task is about **Memory Safety at Startup**, not about adding new features.

---

## Goal (Single Sentence)
Implement a **Memory Contract Validation mechanism** that runs at RAE startup and verifies that the database schema exactly matches the expected structure.

---

## High-Level Requirements (Must Follow)

### 1. No Silent Auto-Migrations
- The system MUST NOT modify the database automatically in default mode.
- Validation and migration are separate concerns.

### 2. Fail Fast
- If the schema is invalid or incomplete:
  - RAE MUST refuse to start
  - A clear error message MUST be produced
  - A structured report of differences MUST be available

### 3. Explicit Modes Only
The behavior MUST be controlled by an environment variable:

```env
RAE_DB_MODE=validate   # default
RAE_DB_MODE=init       # initialize empty database
RAE_DB_MODE=migrate   # apply migrations explicitly

### 4. Add and use a single control table, e.g.:
rae_schema_meta (
  schema_name TEXT PRIMARY KEY,
  version TEXT NOT NULL,
  checksum TEXT NOT NULL,
  applied_at TIMESTAMP NOT NULL,
  rae_core_version TEXT NOT NULL
)


1. Co znaczy „bazy agnostyczne” w praktyce (w RAE)

W RAE agnostyczność oznacza:

RAE-core nie zna konkretnej bazy

zna tylko kontrakt pamięci

konkretna baza to adapter

Czyli nie:

RAE → Postgres


Tylko:

RAE → MemoryContract → Adapter(Postgres | SQLite | Mongo | Qdrant | …)


To jest idealny punkt na walidację.

2. Gdzie NIE robimy walidacji

❌ Nie w RAE-core
❌ Nie „na sztywno” w SQL
❌ Nie per konkretna baza w logice domenowej

Bo wtedy:

tracisz agnostyczność

duplikujesz logikę

łamiesz separację warstw

3. Gdzie ROBIMY walidację (właściwe miejsce)
✅ Na granicy: Adapter + Contract

Każdy adapter implementuje to samo API walidacyjne:

MemoryAdapter
 ├── connect()
 ├── introspect_schema()
 ├── validate_against(contract)
 └── report()


RAE-core:

nie wie, jak działa Postgres

nie wie, czym jest information_schema

wie tylko:

„czy pamięć spełnia kontrakt”

4. Jak wygląda kontrakt przy agnostycznych bazach

Kontrakt nie jest SQL-em.

To jest logiczny model pamięci, np.:

memory_units:
  episodic_events:
    fields:
      id: uuid (pk)
      timestamp: datetime (required, indexed)
      content: text (required)
      embedding: vector[1536] (optional)


To jest:

semantyka pamięci

nie implementacja

5. Co robi adapter konkretnej bazy
Przykład: PostgresAdapter

tłumaczy kontrakt na:

tabele

kolumny

indeksy

sprawdza:

czy istnieją

czy mają zgodne typy

zwraca wynik logiczny, nie SQL

Przykład: SQLiteAdapter

robi to samo

innymi mechanizmami

ale ten sam raport

RAE-core dostaje:

{
  "valid": false,
  "missing": ["episodic_events.embedding"],
  "type_mismatch": ["timestamp"],
  "adapter": "postgres"
}


I to wystarcza.

6. Co z bazami „nie-schematycznymi” (Mongo, KV)

Tu jest ważna rzecz:
agnostyczność ≠ identyczność

Dla:

Mongo

KV store

object storage

Walidujesz:

kolekcje / bucket

wymagane pola logiczne

indeksy logiczne

metadane wersji

Nie wszystko, ale minimum bezpieczeństwa.

7. Dlaczego to jest wręcz idealne dla RAE

Bo RAE:

nie przechowuje CRUD-owych rekordów

przechowuje pamięć poznawczą

potrzebuje:

spójności

izolacji

audytowalności

A to zawsze można opisać kontraktem.

8. Jedno zdanie, które wszystko spina

RAE nie waliduje baz danych.
RAE waliduje kontrakt pamięci, a adapter sprawdza, czy dana baza go spełnia.

To jest klucz.

9. Co to daje praktycznie

agnostyczność zostaje ✔

bezpieczeństwo rośnie ✔

benchmarki mają sens ✔

migracje przestają być „na wiarę” ✔

system staje się deterministyczny

10. Jeśli chcesz iść dalej (opcjonalnie)

Następny poziom to:

Contract checksum

Adapter capability matrix (np. „ten backend nie wspiera vector indexów”)

Partial compliance (np. warn vs fail)

Ale to już etap 2.

Jeśli chcesz, w kolejnym kroku mogę:

rozpisać minimalny interfejs MemoryAdapter.validate()

albo przygotować schemat kontraktu w YAML/JSON

albo sprawdzić, czy to, co już masz w RAE, da się pod to „podpiąć” bez dużego refaktoru

To pytanie, które zadałeś, to dokładnie właściwy moment architektoniczny.

To też Gemini musi wziąć pod uwagę bo agnostycznosc dotyczy też cache i storage

Tak. To jest krytyczne — i bardzo dobrze, że to doprecyzowałeś.
Jeśli Gemini tego nie uwzględni, to „naprawi” DB kosztem złamania architektury RAE.

Poniżej masz jasną, twardą ramę, którą musi wziąć pod uwagę, oraz gotowy fragment, który możesz dopisać do pliku dla Gemini (albo wysłać mu osobno).

1. Najważniejsze zdanie (do zapamiętania)

Agnostyczność w RAE dotyczy nie tylko baz danych, ale również cache i storage.
Walidacji podlega kontrakt pamięci, a nie technologia backendu.

To jest core invariant.

2. Co to znaczy praktycznie (bez teorii)

RAE ma trzy klasy backendów pamięci:

Warstwa	Przykłady	Charakter
Database	Postgres, SQLite, Mongo	trwała pamięć strukturalna
Cache	Redis, in-memory, disk-cache	nietrwała / półtrwała
Storage	FS, S3, object store	blob / artefakty

Każda z nich:

jest agnostyczna

ma adapter

musi spełnić ten sam kontrakt logiczny

3. Jak wygląda walidacja w takim świecie
❌ ZŁE podejście (częsty błąd)

jeden walidator DB

SQL w core

cache pomijany („bo to cache”)

storage niezweryfikowany

✅ DOBRE podejście (RAE-grade)
MemoryContract
 ├── persistence (DB)
 ├── acceleration (Cache)
 └── artifacts (Storage)


I dla każdej warstwy:

ten sam kontrakt logiczny

inny adapter

inny sposób introspekcji

4. Minimalny wspólny interfejs (must-have)

Każdy backend (DB / cache / storage) musi implementować:

class MemoryBackendAdapter:
    def connect(self) -> None
    def introspect(self) -> BackendState
    def validate(self, contract: MemoryContract) -> ValidationResult
    def capabilities(self) -> CapabilityMatrix


RAE-core:

nie wie, czy to Redis czy S3

wie tylko: czy spełnia kontrakt

5. Co znaczy „walidacja” dla cache i storage
Cache (Redis / memory)

Walidujesz:

namespace / prefix

TTL support

eviction policy (jeśli wymagana)

wersję schematu kluczy

isolation (np. tenant / agent)

Nie walidujesz:

istnienia danych (bo to cache)

Storage (FS / S3 / object store)

Walidujesz:

istnienie bucket / katalogu

prawa zapisu / odczytu

layout logiczny (np. /artifacts/{agent_id}/)

metadane wersji

Nie walidujesz:

zawartości plików (to inny proces)

6. Kluczowa reguła projektowa (bardzo ważna)

RAE nie waliduje implementacji.
RAE waliduje zdolność backendu do bycia nośnikiem pamięci zgodnie z kontraktem.

To rozwiązuje:

DB

cache

storage

przyszłe backendy

7. GOTOWY FRAGMENT DO DOPISANIA DO PLIKU DLA GEMINI

Możesz to wkleić 1:1 do poprzedniego .md:

## Critical Architectural Constraint (Must Not Be Violated)

RAE is backend-agnostic not only for databases, but also for:
- cache backends
- storage / artifact backends

The Memory Contract validation mechanism MUST:
- operate on an abstract memory contract
- NOT assume SQL, tables, or schemas in core logic
- be implemented via backend adapters

Validation MUST be supported for:
- persistent databases
- cache layers (Redis, in-memory, etc.)
- storage layers (filesystem, object storage)

Each backend type must validate its ability to fulfill the memory contract
using backend-specific introspection, without leaking implementation details
into RAE-core.

8. Dlaczego to jest tak ważne (w jednym zdaniu)

Bo w RAE:

technologie będą się zmieniać, a pamięć musi pozostać poprawna.

To jest system długowieczny, nie jednorazowa aplikacja.

9. Co bym sprawdził po pracy Gemini (checklist)

brak SQL w core

jeden interfejs walidacji

cache i storage nie są pominięte

kontrakt jest logiczny, nie implementacyjny

backend mówi „nie spełniam kontraktu” zamiast „jakoś działa”

Jeśli chcesz, następnym krokiem mogę:

przygotować pełny MemoryContract (DB + cache + storage) w YAML

albo review-prompt dla Gemini: „sprawdź czy nie złamałeś agnostyczności”
