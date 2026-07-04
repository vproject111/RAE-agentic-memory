# apps/memory-api/metrics.py
import time

from prometheus_client import Counter, Gauge, Histogram

# --- Custom Metrics ---
LABELS = ["tenant_id", "project"]

# --- Operational Metrics (Layer 1) ---
_START_TIME = time.time()
rae_uptime_seconds = Gauge("rae_uptime_seconds", "Uptime of the RAE service in seconds")
rae_uptime_seconds.set_function(lambda: time.time() - _START_TIME)

rae_memory_count_total = Gauge(
    "rae_memory_count_total",
    "Total count of memories in the system",
    ["tenant_id", "layer", "memory_type"],
)
rae_sync_last_success_timestamp = Gauge(
    "rae_sync_last_success_timestamp",
    "Timestamp of the last successful sync",
    ["tenant_id", "target_node", "peer_id", "direction"],
)
rae_active_sessions = Gauge(
    "rae_active_sessions", "Number of active user sessions", ["tenant_id"]
)
rae_reflection_processing_seconds = Histogram(
    "rae_reflection_processing_seconds",
    "Histogram of reflection processing duration in seconds",
    ["tenant_id", "reflection_type"],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, float("inf")),
)

rae_api_requests_total = Counter(
    "rae_api_requests_total",
    "Total number of API requests processed",
    ["tenant_id", "method", "endpoint", "status"],
)
rae_errors_total = Counter(
    "rae_errors_total",
    "Total number of errors encountered",
    ["tenant_id", "endpoint", "error_type", "http_status", "component"],
)

memory_store_counter = Counter(
    "memory_store_total", "Total number of memory store operations", ["tenant_id"]
)
memory_query_counter = Counter(
    "memory_query_total", "Total number of memory query operations", ["tenant_id"]
)
memory_delete_counter = Counter(
    "memory_delete_total", "Total number of memory delete operations", ["tenant_id"]
)
llm_cost_counter = Counter(
    "llm_cost_usd_total", "Cumulative cost of LLM calls in USD", LABELS
)

# --- Cost Controller Metrics (Enterprise Cost Tracking) ---
# These metrics provide comprehensive cost and token observability for LLM usage

# Total LLM costs by tenant/project (cumulative counter)
rae_cost_llm_total_usd = Counter(
    "rae_cost_llm_total_usd",
    "Total cumulative LLM costs in USD",
    ["tenant_id", "project", "model", "provider"],
)

# Daily and Monthly cost gauges (reset at boundaries)
rae_cost_llm_daily_usd = Gauge(
    "rae_cost_llm_daily_usd",
    "Current daily LLM costs in USD (resets at midnight UTC)",
    ["tenant_id", "project"],
)

rae_cost_llm_monthly_usd = Gauge(
    "rae_cost_llm_monthly_usd",
    "Current monthly LLM costs in USD (resets on 1st of month)",
    ["tenant_id", "project"],
)

# Token usage tracking
rae_cost_llm_tokens_used = Counter(
    "rae_cost_llm_tokens_used",
    "Total cumulative tokens used (input + output)",
    ["tenant_id", "project", "model", "provider"],
)

# Cache savings tracking
rae_cost_cache_saved_usd = Counter(
    "rae_cost_cache_saved_usd",
    "Estimated cost savings from cache hits in USD",
    ["tenant_id", "project"],
)

# Budget enforcement tracking
rae_cost_budget_rejections_total = Counter(
    "rae_cost_budget_rejections_total",
    "Total number of requests rejected due to budget limits",
    [
        "tenant_id",
        "project",
        "limit_type",
    ],  # limit_type: daily_usd, monthly_usd, daily_tokens, monthly_tokens
)

# LLM call counting
rae_cost_llm_calls_total = Counter(
    "rae_cost_llm_calls_total",
    "Total number of LLM API calls",
    ["tenant_id", "project", "model", "provider", "operation"],
)

# Token distribution analysis
rae_cost_tokens_per_call_histogram = Histogram(
    "rae_cost_tokens_per_call",
    "Distribution of tokens used per LLM call",
    ["model", "provider"],
    buckets=[100, 500, 1000, 2000, 5000, 10000, 20000, 50000, 100000, 200000],
)
deduplication_hit_counter = Counter(
    "memory_deduplication_hit_total",
    "Total number of deduplication hits",
    ["tenant_id"],
)
reflection_event_counter = Counter(
    "memory_reflection_event_total", "Total number of reflection events", LABELS
)
embedding_time_histogram = Histogram(
    "embedding_time_seconds", "Time taken for embedding generation"
)
vector_query_time_histogram = Histogram(
    "vector_query_time_seconds", "Time taken for vector store queries"
)

# --- Cache Metrics ---
cache_hit_counter = Counter(
    "cache_hit_total",
    "Total number of cache hits",
    ["tenant_id", "project", "cache_type"],
)
cache_miss_counter = Counter(
    "cache_miss_total",
    "Total number of cache misses",
    ["tenant_id", "project", "cache_type"],
)
cache_rebuild_time_gauge = Gauge(
    "cache_rebuild_time_seconds", "Time taken for the last cache rebuild"
)
cache_size_gauge = Gauge(
    "cache_size_mb", "Size of the cache in MB", ["cache_type", "project"]
)

# --- Reflective Memory Metrics ---
# These metrics track the Reflective Memory V1 system operations

# Decay operations
rae_reflective_decay_updated_total = Counter(
    "rae_reflective_decay_updated_total",
    "Total number of memories updated by decay worker",
    ["tenant_id"],
)

rae_reflective_decay_duration_seconds = Histogram(
    "rae_reflective_decay_duration_seconds",
    "Time taken for decay cycle to complete",
    ["tenant_id"],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600],
)

# Dreaming operations
rae_reflective_dreaming_reflections_generated = Counter(
    "rae_reflective_dreaming_reflections_generated",
    "Total number of reflections generated by dreaming worker",
    ["tenant_id", "project"],
)

rae_reflective_dreaming_episodes_analyzed = Counter(
    "rae_reflective_dreaming_episodes_analyzed",
    "Total number of episodes analyzed during dreaming",
    ["tenant_id", "project"],
)

rae_reflective_dreaming_duration_seconds = Histogram(
    "rae_reflective_dreaming_duration_seconds",
    "Time taken for dreaming cycle to complete",
    ["tenant_id"],
    buckets=[1, 5, 10, 30, 60, 120, 300],
)

# Summarization operations
rae_reflective_summarization_summaries_created = Counter(
    "rae_reflective_summarization_summaries_created",
    "Total number of session summaries created",
    ["tenant_id", "project"],
)

rae_reflective_summarization_events_summarized = Counter(
    "rae_reflective_summarization_events_summarized",
    "Total number of events summarized",
    ["tenant_id", "project"],
)

rae_reflective_summarization_duration_seconds = Histogram(
    "rae_reflective_summarization_duration_seconds",
    "Time taken for summarization to complete",
    ["tenant_id"],
    buckets=[0.5, 1, 2, 5, 10, 30, 60],
)

# Context builder operations
rae_reflective_context_reflections_retrieved = Histogram(
    "rae_reflective_context_reflections_retrieved",
    "Number of reflections retrieved per context building",
    ["tenant_id", "mode"],
    buckets=[0, 1, 2, 3, 5, 10, 20],
)

# Mode tracking
rae_reflective_mode_gauge = Gauge(
    "rae_reflective_mode",
    "Current reflective memory mode (0=disabled, 1=lite, 2=full)",
    [],
)

# Flag tracking
rae_reflective_flags_gauge = Gauge(
    "rae_reflective_flags",
    "Reflective memory feature flags status (0=disabled, 1=enabled)",
    ["flag"],  # flag: reflective_enabled, dreaming_enabled, summarization_enabled
)

# --- ISO/IEC 42001 Compliance Metrics ---
# These metrics track compliance with ISO 42001 AI Management System standard

# Overall compliance score
rae_iso42001_compliance_score = Gauge(
    "rae_iso42001_compliance_score",
    "Overall ISO 42001 compliance score (0-100)",
    ["tenant_id", "area"],  # area: governance, risk_mgmt, data_mgmt, transparency, etc.
)

# Compliance requirement tracking
rae_iso42001_requirements_total = Gauge(
    "rae_iso42001_requirements_total",
    "Total number of ISO 42001 requirements tracked",
    ["tenant_id", "area"],
)

rae_iso42001_requirements_compliant = Gauge(
    "rae_iso42001_requirements_compliant",
    "Number of compliant ISO 42001 requirements",
    ["tenant_id", "area"],
)

# Audit trail metrics
rae_iso42001_audit_trail_completeness = Gauge(
    "rae_iso42001_audit_trail_completeness",
    "Percentage of events with complete audit trail (0-100)",
    ["tenant_id", "event_type"],
)

rae_iso42001_audit_entries_total = Counter(
    "rae_iso42001_audit_entries_total",
    "Total number of audit trail entries created",
    ["tenant_id", "event_type", "actor_type"],
)

# Data retention compliance
rae_iso42001_data_retention_compliance = Gauge(
    "rae_iso42001_data_retention_compliance",
    "Percentage of data meeting retention policies (0-100)",
    ["tenant_id", "data_class"],
)

rae_iso42001_expired_data_records = Gauge(
    "rae_iso42001_expired_data_records",
    "Number of records past retention period pending deletion",
    ["tenant_id", "data_class"],
)

rae_iso42001_data_deletions_total = Counter(
    "rae_iso42001_data_deletions_total",
    "Total number of records deleted per retention policy",
    ["tenant_id", "data_class", "deletion_reason"],
)

# Risk register metrics
rae_iso42001_risks_total = Gauge(
    "rae_iso42001_risks_total",
    "Total number of identified risks in risk register",
    ["tenant_id", "risk_level"],  # risk_level: critical, high, medium, low
)

rae_iso42001_risks_open = Gauge(
    "rae_iso42001_risks_open",
    "Number of open (unmitigated) risks",
    ["tenant_id", "risk_level"],
)

rae_iso42001_risks_mitigated = Gauge(
    "rae_iso42001_risks_mitigated",
    "Number of mitigated risks",
    ["tenant_id", "risk_level"],
)

rae_iso42001_risk_register_last_review_days = Gauge(
    "rae_iso42001_risk_register_last_review_days",
    "Days since risk register was last updated",
    ["tenant_id"],
)

# Source trust metrics
rae_iso42001_source_trust_distribution = Gauge(
    "rae_iso42001_source_trust_distribution",
    "Distribution of source trust levels",
    ["tenant_id", "trust_level"],  # trust_level: high, medium, low, unverified
)

rae_iso42001_source_trust_verified_percentage = Gauge(
    "rae_iso42001_source_trust_verified_percentage",
    "Percentage of sources with verified trust level (0-100)",
    ["tenant_id"],
)

rae_iso42001_sources_pending_verification = Gauge(
    "rae_iso42001_sources_pending_verification",
    "Number of sources pending verification",
    ["tenant_id"],
)

# Human oversight metrics
rae_iso42001_human_oversight_decisions = Counter(
    "rae_iso42001_human_oversight_decisions",
    "Number of human-in-the-loop oversight decisions",
    ["tenant_id", "decision_type"],  # decision_type: approval, rejection, escalation
)

rae_iso42001_ai_decisions_total = Counter(
    "rae_iso42001_ai_decisions_total",
    "Total number of AI system decisions",
    ["tenant_id", "decision_category", "confidence_level"],
)

rae_iso42001_ai_decisions_overridden = Counter(
    "rae_iso42001_ai_decisions_overridden",
    "Number of AI decisions overridden by humans",
    ["tenant_id", "decision_category", "override_reason"],
)

# Model governance metrics
rae_iso42001_models_deployed = Gauge(
    "rae_iso42001_models_deployed",
    "Number of AI models currently deployed",
    ["tenant_id", "model_type"],
)

rae_iso42001_model_cards_completeness = Gauge(
    "rae_iso42001_model_cards_completeness",
    "Percentage of deployed models with complete model cards (0-100)",
    ["tenant_id"],
)

# Transparency and explainability
rae_iso42001_explainability_requests = Counter(
    "rae_iso42001_explainability_requests",
    "Number of AI decision explainability requests",
    ["tenant_id", "explanation_type"],
)

rae_iso42001_data_subject_requests = Counter(
    "rae_iso42001_data_subject_requests",
    "Number of GDPR data subject requests processed",
    ["tenant_id", "request_type"],  # request_type: access, erasure, rectification
)

# Row-Level Security (RLS) metrics
rae_iso42001_rls_tables_enabled = Gauge(
    "rae_iso42001_rls_tables_enabled",
    "Number of database tables with RLS enabled",
    ["tenant_id"],
)

rae_iso42001_rls_policies_active = Gauge(
    "rae_iso42001_rls_policies_active",
    "Number of active RLS policies",
    ["tenant_id"],
)

rae_iso42001_rls_verification_status = Gauge(
    "rae_iso42001_rls_verification_status",
    "RLS verification status (1=passed, 0=failed)",
    ["tenant_id"],
)

rae_iso42001_rls_context_set_total = Counter(
    "rae_iso42001_rls_context_set_total",
    "Total number of RLS context settings",
    ["tenant_id", "context_type"],  # context_type: http_request, background_task
)

rae_iso42001_rls_context_failures = Counter(
    "rae_iso42001_rls_context_failures",
    "Number of RLS context setting failures",
    ["tenant_id", "failure_reason"],
)

# Certification readiness
rae_iso42001_certification_ready = Gauge(
    "rae_iso42001_certification_ready",
    "Certification readiness indicator (1=ready, 0=not ready)",
    ["tenant_id"],
)

rae_iso42001_critical_gaps_count = Gauge(
    "rae_iso42001_critical_gaps_count",
    "Number of critical compliance gaps",
    ["tenant_id"],
)

# Compliance checks
rae_iso42001_compliance_checks_total = Counter(
    "rae_iso42001_compliance_checks_total",
    "Total number of compliance checks performed",
    ["tenant_id", "check_type", "result"],  # result: passed, failed, warning
)
