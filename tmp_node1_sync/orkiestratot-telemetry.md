1. Co śledzimy – 3 warstwy telemetry dla orkiestratora
1) Traces (śledzenie przepływu)

Każde uruchomienie orkiestratora / taska = główny trace, np.:

orchestrator.run – jedno odpalenie „sesji” orkiestratora.

task.run – dla każdego taska z tasks.yaml.

step.run – dla każdego kroku planu.

llm.call – każde wywołanie:

Gemini (CLI),

Claude (API/CLI),

lokalny model.

W atrybutach spanów trzymasz m.in.:

task.id, task.area, task.risk,

step.id, step.type (plan, review_plan, implement, review_code, quality_gate),

llm.provider (gemini_cli, claude_api, local_ollama),

llm.model_name,

llm.role (planner, plan_reviewer, implementer, code_reviewer),

result.status (success, fail, retry, human_required).

To da Ci „film” z jednej iteracji: kto co robił, w jakiej kolejności i gdzie się wysypało.

2) Metrics (metryki ilościowe)

Kilka kluczowych liczników / mierników:

Task-level:

orchestrator_tasks_total{status=...}
– ile zadań zakończonych success/fail/human_required.

orchestrator_task_duration_seconds (histogram)
– ile realnie trwa task od NEW do DONE.

Step-level:

orchestrator_steps_total{type=..., status=...}
– ile kroków implementacji, review, quality gate itd. i ile z nich failuje.

LLM usage:

orchestrator_llm_calls_total{provider, model, role}
– ile razy który model był Plannerem, Implementerem, Reviewerem.

(jeśli masz dane o kosztach/tokens) orchestrator_llm_tokens_total{provider, model}
– potem możesz zobaczyć koszt per task / per repo.

Quality Gate:

orchestrator_quality_gate_runs_total{status}
– ile razy były odpalane testy i ile razy fail.

orchestrator_quality_regressions_total{type}
– np. tests_failed, warnings_new, coverage_drop.

Dzięki temu po miesiącu będziesz mógł odpowiedzieć na pytania typu:

„Który model najczęściej daje kod wymagający poprawek?”

„Ile retry zwykle potrzeba przy high-risk steps?”

„Czy w ogóle poprawiamy jakość, czy tylko mielimy pętlą?”

3) Logs (szczegóły tekstowe)

Nie wszystko trzeba upychać w spanach – niech orkiestrator:

loguje każdą decyzję routingu:

„Task RAE-MATH-001 / step S2 → implementer = gemini_flash, reviewer = claude_sonnet”

loguje powody failed quality gate:

„pytest failed: 3 tests failing (lista nazw)”

„ruff: nowy warning w pliku X…”

loguje konflikty między modelami:

„Code-Reviewer odrzucił patch Implementer-Agent z powodu XYZ”.

Te logi też możesz wysyłać przez OpenTelemetry (OTel logs) do tego samego backendu co traces/metrics.

2. Jak to technicznie spiąć (minimalna wersja)

Zakładam, że orkiestrator piszesz w Pythonie i masz już OTel w RAE/math/CI.
Orkiestrator robi:

Inicjalizacja OTel na starcie:

tracer (TracerProvider),

meter (MeterProvider),

exporter OTLP do Twojego Jaegera/Grafany/Tempo/etc.

W main.py:

startujesz span = tracer.start_as_current_span("orchestrator.run"),

w nim:

pętla po taskach → każdy task nowy span task.run,

w tasku:

plan → span("task.plan"),

review planu,

implementacja kroków,

quality gate.

Przy wywołaniu LLM-a:

wrapper np. call_llm(provider, role, prompt, context):

tworzy span llm.call,

zapisuje atrybuty: provider, model, role, prompt_size, itp.,

odpala subprocess na gemini albo HTTP na Claude’a,

zapisuje status (success/fail, ewentualnie error).