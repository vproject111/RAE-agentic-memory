RAE – OpenTelemetry Implementation Plan (4 Iteracje)
Cel dokumentu

Wprowadzić pełną, stabilną i testowalną integrację OpenTelemetry do projektu RAE (FastAPI + Celery + Redis + Postgres + Qdrant + warstwa Reflective Memory).
Plan ma formę iteracyjną, aby wdrożenie było bezpieczne i zgodne z architekturą projektu.

Iteracja 1 – Fundamenty OTEL + Instrumentacja FastAPI
Cel

Włączyć minimalną telemetrię backendu RAE: requesty, błędy, trace’y.

Zakres

instalacja zależności OTEL

konfiguracja TracerProvider

konfiguracja OTLP exporter → Collector

globalny tracer + metryki

automatyczna instrumentacja FastAPI

Do zrobienia

Dodać do pyproject.toml:

opentelemetry-api
opentelemetry-sdk
opentelemetry-exporter-otlp
opentelemetry-instrumentation-fastapi
opentelemetry-instrumentation-asgi


Utworzyć plik:
rae_core/observability/otel_setup.py, który:

tworzy TracerProvider

dodaje OTLPSpanExporter

rejestruje BatchSpanProcessor

W main.py dodać hook inicjalizujący OTEL.

Dodać konfigurację Collector (docker compose):

odbiór OTLP (gRPC / HTTP)

eksport do Jaeger / Tempo

Dodać zmienne środowiskowe:

OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
OTEL_SERVICE_NAME=rae-core

Testy (automatyczne i manualne)
Testy jednostkowe

test_otel_setup.py

inicjalizacja providera bez wyjątków

poprawność konfiguracji exporterów

czy tracer jest singletonem

Testy integracyjne

wywołanie /api/health → collector powinien wysłać trace

trace ma atrybuty:

http.method

http.url

service.name == "rae-core"

Testy E2E

uruchomić docker compose z OTEL Collector + Jaeger

wykonać kilka requestów

sprawdzić w Jaegerze poprawność timeline’u

Kryteria ukończenia

FastAPI generuje trace’y

Collector odbiera trace’y

testy jednostkowe i E2E przechodzą

żadnych crashy przy starcie usługi
