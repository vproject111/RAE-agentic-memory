# RAE OpenTelemetry Research Guide

## Table of Contents

- [Introduction](#introduction)
- [RAE Telemetry Schema v1](#rae-telemetry-schema-v1)
- [Setting Up for Research](#setting-up-for-research)
- [Understanding the Data](#understanding-the-data)
- [Query Examples](#query-examples)
- [Data Analysis Workflows](#data-analysis-workflows)
- [Experiment Tracking](#experiment-tracking)
- [Compliance and Ethics](#compliance-and-ethics)
- [Advanced Topics](#advanced-topics)

---

## Introduction

This guide is for AI researchers and data scientists who want to use RAE's OpenTelemetry instrumentation for research purposes.

### What You Can Study

RAE's telemetry provides rich, structured data about:

- **Agent Behavior**: How agents decompose tasks, reason, and make decisions
- **Memory Systems**: Effectiveness of episodic, semantic, graph, and reflective memory
- **Reasoning Patterns**: Step-by-step reasoning traces with confidence scores
- **LLM Usage**: Token consumption, costs, and model performance
- **Outcomes**: Success rates, accuracy, and failure modes
- **Safety**: Intervention patterns and guardrail effectiveness

### Research Philosophy

> **"Full signal inside, different views outside"**

RAE collects comprehensive telemetry internally, then applies different filters and sampling based on the deployment profile. This ensures:

1. **Reproducibility**: Consistent attribute names across studies
2. **Comparability**: Standard metrics enable cross-study comparisons
3. **Privacy**: PII scrubbing for sensitive environments
4. **Flexibility**: Export to various formats (OTLP, Parquet, CSV)

---

## RAE Telemetry Schema v1

### Schema Overview

The RAE Telemetry Schema v1 defines standardized attribute names organized into 12 categories:

| Category | Prefix | Description |
|----------|--------|-------------|
| Agent | `rae.agent.*` | Agent identification and roles |
| Memory | `rae.memory.*` | Memory layer operations |
| Reasoning | `rae.reasoning.*` | Reasoning process tracking |
| LLM | `rae.llm.*` | LLM usage and configuration |
| Cost | `rae.cost.*` | Token usage and costs |
| Safety | `rae.safety.*` | Safety interventions |
| Outcome | `rae.outcome.*` | Task outcomes and quality |
| Correlation | `rae.session.*`, `rae.task.*` | Correlation identifiers |
| Experiment | `rae.experiment.*` | A/B testing and experiments |
| Performance | `rae.performance.*` | Latency and throughput |
| Data Quality | `rae.data.*` | Data completeness and validity |
| Human | `rae.human.*` | Human-in-the-loop tracking |

### Key Attributes

#### Agent Attributes

```python
rae.agent.role          # Agent role: planner, evaluator, worker, router, etc.
rae.agent.id            # Unique agent instance ID
rae.agent.version       # Agent version
rae.agent.state         # Agent state: active, paused, terminated
```

#### Memory Attributes

```python
rae.memory.layer                 # Memory layer: episodic, semantic, graph, reflective
rae.memory.operation             # Operation: create, read, update, delete, search
rae.memory.access_count          # Number of memory accesses
rae.memory.hit_rate              # Cache hit rate (0.0-1.0)
rae.memory.vector_count          # Number of vectors processed
rae.memory.similarity_threshold  # Search similarity threshold
rae.memory.graph_nodes           # Number of graph nodes
rae.memory.graph_edges           # Number of graph edges
rae.memory.importance_score      # Memory importance (0.0-1.0)
```

#### Reasoning Attributes

```python
rae.reasoning.step_type          # Step type: decompose, retrieve, reflect, revise, decide
rae.reasoning.step_number        # Step number in sequence
rae.reasoning.total_steps        # Total steps in reasoning chain
rae.reasoning.depth              # Nesting depth of reasoning
rae.reasoning.iterations         # Number of iterations
rae.reasoning.confidence         # Confidence score (0.0-1.0)
rae.reasoning.uncertainty        # Uncertainty score (0.0-1.0)
```

#### Cost Attributes

```python
rae.cost.tokens_input       # Input tokens
rae.cost.tokens_output      # Output tokens
rae.cost.tokens_total       # Total tokens
rae.cost.usd                # Cost in USD
```

#### Outcome Attributes

```python
rae.outcome.label           # Outcome: success, fail, uncertain, needs_human
rae.outcome.success_rate    # Success rate (0.0-1.0)
rae.outcome.accuracy        # Accuracy score (0.0-1.0)
rae.outcome.f1_score        # F1 score (0.0-1.0)
```

#### Correlation Attributes

```python
rae.session.id              # User/agent session ID
rae.task.id                 # Top-level task ID
rae.subtask.id              # Subtask ID
rae.experiment.id           # Experiment ID
```

### Enum Values

**Agent Roles:**
- `planner`, `evaluator`, `worker`, `router`, `reflector`, `synthesizer`, `orchestrator`

**Memory Layers:**
- `episodic`, `semantic`, `reflective`, `graph`, `working`, `long_term`

**Reasoning Steps:**
- `decompose`, `retrieve`, `reflect`, `revise`, `decide`, `synthesize`, `plan`, `evaluate`

**Outcomes:**
- `success`, `fail`, `uncertain`, `needs_human`, `timeout`, `cancelled`

---

## Setting Up for Research

### 1. Configure Research Profile

Set the telemetry profile to `research`:

```bash
export RAE_TELEMETRY_PROFILE=research
export OTEL_CONFIG_FILE=config/otel_research.yaml
```

The research profile provides:
- 100% sampling (full data collection)
- PII anonymization (not scrubbing)
- 90-day retention
- Export to multiple formats

### 2. Choose Export Format

**For Interactive Analysis (Jupyter):**
```bash
export OTEL_EXPORTER_TYPE=otlp
# Data available via Jaeger UI and API
```

**For Large-Scale Analysis:**
```bash
export CLICKHOUSE_ENABLED=true
export CLICKHOUSE_ENDPOINT=http://localhost:8123
# Export to ClickHouse for SQL queries
```

**For Offline Analysis:**
```bash
export TRACES_EXPORT_PATH=/data/traces
# Export to JSONL files for pandas/dask
```

### 3. Start Collection

```bash
# Start RAE with research profile
docker compose up -d

# Verify telemetry is working
curl http://localhost:16686  # Jaeger UI
```

---

## Understanding the Data

### Trace Structure

Each trace represents a complete task execution:

```
Trace (rae.task.id)
└── Root Span (task execution)
    ├── Agent Span (agent.role=planner)
    │   └── Reasoning Span (reasoning.step_type=decompose)
    │       └── LLM Span (llm.model=gpt-4)
    ├── Memory Span (memory.layer=semantic, memory.operation=search)
    │   └── Vector Search Span (qdrant.search)
    └── Outcome Span (outcome.label=success)
```

### Span Relationships

- **Parent-Child**: Hierarchical operation nesting
- **Correlation**: Link spans via `rae.session.id`, `rae.task.id`
- **Causality**: Follow reasoning chains via `rae.reasoning.step_number`

### Time Series Data

All spans include timestamps:
- `start_time`: Span start (nanoseconds since epoch)
- `end_time`: Span end
- `duration`: `end_time - start_time`

---

## Query Examples

### SQL Queries (ClickHouse)

**1. Average Tokens by Memory Layer**

```sql
SELECT
    attributes['rae.memory.layer'] AS memory_layer,
    AVG(toFloat64(attributes['rae.cost.tokens_total'])) AS avg_tokens,
    COUNT(*) AS operation_count
FROM traces
WHERE attributes['rae.memory.layer'] IS NOT NULL
GROUP BY memory_layer
ORDER BY avg_tokens DESC;
```

**2. Success Rate by Agent Role**

```sql
SELECT
    attributes['rae.agent.role'] AS agent_role,
    countIf(attributes['rae.outcome.label'] = 'success') / COUNT(*) AS success_rate,
    COUNT(*) AS total_tasks
FROM traces
WHERE attributes['rae.agent.role'] IS NOT NULL
GROUP BY agent_role
ORDER BY success_rate DESC;
```

**3. Reasoning Depth vs. Outcome**

```sql
SELECT
    toInt32(attributes['rae.reasoning.depth']) AS depth,
    attributes['rae.outcome.label'] AS outcome,
    COUNT(*) AS count,
    AVG(toFloat64(attributes['rae.reasoning.confidence'])) AS avg_confidence
FROM traces
WHERE attributes['rae.reasoning.depth'] IS NOT NULL
GROUP BY depth, outcome
ORDER BY depth, outcome;
```

**4. Cost Analysis by Model**

```sql
SELECT
    attributes['rae.llm.model'] AS model,
    SUM(toFloat64(attributes['rae.cost.usd'])) AS total_cost_usd,
    SUM(toInt64(attributes['rae.cost.tokens_total'])) AS total_tokens,
    AVG(duration_ms) AS avg_latency_ms
FROM traces
WHERE attributes['rae.llm.model'] IS NOT NULL
GROUP BY model
ORDER BY total_cost_usd DESC;
```

**5. Memory Hit Rate Trends**

```sql
SELECT
    toDate(timestamp) AS date,
    attributes['rae.memory.layer'] AS layer,
    AVG(toFloat64(attributes['rae.memory.hit_rate'])) AS avg_hit_rate
FROM traces
WHERE attributes['rae.memory.hit_rate'] IS NOT NULL
GROUP BY date, layer
ORDER BY date, layer;
```

### Jaeger UI Queries

**Find All Planner Operations:**
```
service:rae-memory-api
tag:rae.agent.role:planner
```

**Find Failed Tasks:**
```
service:rae-memory-api
tag:rae.outcome.label:fail
minDuration:1s
```

**Find Expensive LLM Calls:**
```
service:rae-memory-api
tag:rae.cost.usd:>0.01
```

### PromQL Queries (Metrics)

**Memory Operation Rate:**
```promql
rate(rae_memory_operations_total[5m])
```

**P95 Latency by Layer:**
```promql
histogram_quantile(0.95,
  rate(rae_performance_latency_ms_bucket[5m])
)
```

**Token Consumption Rate:**
```promql
rate(rae_cost_tokens_total[1h])
```

---

## Data Analysis Workflows

### Workflow 1: Memory Effectiveness Study

**Research Question**: Which memory layer is most effective for long-term retention?

**Steps:**

1. **Export Data**
```bash
# Export 30 days of memory operations
python scripts/export_traces.py \
  --profile research \
  --filter "rae.memory.layer:*" \
  --format parquet \
  --output /data/memory_study.parquet
```

2. **Load in Pandas**
```python
import pandas as pd

df = pd.read_parquet('/data/memory_study.parquet')

# Filter to memory operations
memory_df = df[df['rae.memory.operation'].notna()]

# Group by layer
results = memory_df.groupby('rae.memory.layer').agg({
    'rae.memory.access_count': 'sum',
    'rae.memory.hit_rate': 'mean',
    'rae.performance.latency_ms': ['mean', 'p95'],
    'rae.outcome.label': lambda x: (x == 'success').mean()
}).round(3)

print(results)
```

3. **Visualize**
```python
import matplotlib.pyplot as plt

results['rae.memory.hit_rate'].plot(kind='bar')
plt.title('Memory Hit Rate by Layer')
plt.ylabel('Hit Rate')
plt.show()
```

### Workflow 2: Reasoning Pattern Analysis

**Research Question**: Do deeper reasoning chains lead to better outcomes?

**Query:**
```sql
SELECT
    reasoning_depth,
    AVG(confidence) AS avg_confidence,
    success_rate,
    COUNT(*) AS sample_size
FROM (
    SELECT
        toInt32(attributes['rae.reasoning.depth']) AS reasoning_depth,
        toFloat64(attributes['rae.reasoning.confidence']) AS confidence,
        toFloat64(attributes['rae.outcome.accuracy']) AS accuracy,
        IF(attributes['rae.outcome.label'] = 'success', 1, 0) AS success
    FROM traces
    WHERE attributes['rae.reasoning.depth'] IS NOT NULL
)
GROUP BY reasoning_depth
HAVING sample_size > 100  -- Statistical significance
ORDER BY reasoning_depth;
```

**Analysis:**
```python
# Correlation analysis
import scipy.stats as stats

correlation, p_value = stats.pearsonr(
    df['reasoning_depth'],
    df['success_rate']
)

print(f"Correlation: {correlation:.3f}, p={p_value:.4f}")
```

### Workflow 3: Cost Optimization

**Research Question**: Can we reduce costs without impacting quality?

**Steps:**

1. **Identify Cost Drivers**
```sql
SELECT
    attributes['rae.llm.model'] AS model,
    attributes['rae.memory.layer'] AS layer,
    SUM(toFloat64(attributes['rae.cost.usd'])) AS total_cost,
    AVG(toFloat64(attributes['rae.outcome.accuracy'])) AS avg_accuracy
FROM traces
GROUP BY model, layer
ORDER BY total_cost DESC
LIMIT 20;
```

2. **A/B Test Cheaper Models**
```python
from apps.memory_api.observability import RAETracingContext

# Set experiment ID
with RAETracingContext.experiment("cost-reduction-v1"):
    # Variant A: GPT-4
    with RAETracingContext.experiment_variant("gpt4"):
        result_a = run_task(model="gpt-4")

    # Variant B: GPT-4o-mini
    with RAETracingContext.experiment_variant("gpt4o-mini"):
        result_b = run_task(model="gpt-4o-mini")
```

3. **Compare Results**
```sql
SELECT
    attributes['rae.experiment.variant'] AS variant,
    AVG(toFloat64(attributes['rae.cost.usd'])) AS avg_cost,
    AVG(toFloat64(attributes['rae.outcome.accuracy'])) AS avg_accuracy,
    COUNT(*) AS n
FROM traces
WHERE attributes['rae.experiment.id'] = 'cost-reduction-v1'
GROUP BY variant;
```

---

## Experiment Tracking

### Setting Up Experiments

**1. Define Experiment**
```python
from apps.memory_api.observability import RAETracingContext

# Start experiment session
with RAETracingContext.experiment(
    experiment_id="memory-retrieval-v2",
    hypothesis="Increasing k from 10 to 20 improves accuracy"
):
    # Your experiment code
    run_experiment()
```

**2. Track Variants**
```python
for k in [5, 10, 15, 20]:
    with RAETracingContext.experiment_variant(f"k={k}"):
        results = semantic_search(query, k=k)
        # Results automatically tagged with variant
```

**3. Query Results**
```sql
SELECT
    attributes['rae.experiment.variant'] AS variant,
    AVG(toFloat64(attributes['rae.outcome.accuracy'])) AS accuracy,
    AVG(toFloat64(attributes['rae.cost.tokens_total'])) AS avg_tokens,
    COUNT(*) AS n
FROM traces
WHERE attributes['rae.experiment.id'] = 'memory-retrieval-v2'
GROUP BY variant
ORDER BY variant;
```

### Statistical Testing

```python
import pandas as pd
from scipy.stats import ttest_ind

# Load experiment data
df = load_experiment_data("memory-retrieval-v2")

# Compare variants
control = df[df['variant'] == 'k=10']['accuracy']
treatment = df[df['variant'] == 'k=20']['accuracy']

t_stat, p_value = ttest_ind(control, treatment)

print(f"t-statistic: {t_stat:.3f}")
print(f"p-value: {p_value:.4f}")
print(f"Significant: {p_value < 0.05}")
```

---

## Compliance and Ethics

### PII Handling

**Research profile** enables PII anonymization:
- Email addresses → `[EMAIL]`
- Phone numbers → `[PHONE]`
- Names → `[NAME]`
- IPs → `[IP_ADDRESS]`

**Verify PII scrubbing:**
```python
from apps.memory_api.observability import has_pii, scrub_pii

text = "Contact john.doe@example.com"
assert has_pii(text)

scrubbed = scrub_pii(text)
assert scrubbed == "Contact [EMAIL]"
```

### Data Retention

Research profile: 90 days retention
```bash
# Check retention policy
cat config/otel_research.yaml | grep retention
```

### Consent and Ethics

Before conducting research:

1. ✅ Obtain IRB approval (if required)
2. ✅ Ensure user consent for data collection
3. ✅ Anonymize PII
4. ✅ Follow institutional data policies
5. ✅ Document methodology

---

## Advanced Topics

### Custom Attributes

Add domain-specific attributes:

```python
from apps.memory_api.observability import add_span_attributes

add_span_attributes(
    custom_metric=0.95,
    research_condition="treatment_a",
    participant_id="anon_123"
)
```

### Distributed Tracing

Track operations across services:

```python
from apps.memory_api.observability import RAETracingContext

# Service A
with RAETracingContext.task("multi-service-task") as task_id:
    # Propagate context to service B
    call_service_b(task_id=task_id)

# Service B
with RAETracingContext.task(task_id):
    # Continue trace in service B
    process_request()
```

### Real-Time Analysis

Stream traces to analytics:

```bash
# Export to Kafka for real-time processing
export OTEL_EXPORTER_TYPE=kafka
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
export KAFKA_TOPIC=rae-traces
```

### Machine Learning on Traces

Train models on trace data:

```python
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

# Load traces
df = pd.read_parquet('/data/traces.parquet')

# Feature engineering
features = [
    'rae.reasoning.depth',
    'rae.memory.access_count',
    'rae.cost.tokens_total',
    'rae.performance.latency_ms'
]

X = df[features]
y = (df['rae.outcome.label'] == 'success').astype(int)

# Train classifier
model = RandomForestClassifier()
model.fit(X, y)

print(f"Accuracy: {model.score(X, y):.3f}")
```

---

## Resources

### Documentation
- [RAE Telemetry Schema Reference](../apps/memory_api/observability/rae_telemetry_schema.py)
- [RAE Tracing Helpers](../apps/memory_api/observability/rae_tracing.py)
- [Telemetry Profiles](../apps/memory_api/observability/telemetry_profiles.py)

### Tools
- [Jaeger UI](http://localhost:16686) - Visual trace explorer
- [ClickHouse](https://clickhouse.com/docs) - SQL analytics
- [Pandas](https://pandas.pydata.org/docs/) - Data analysis
- [Grafana](https://grafana.com/docs/) - Dashboards

### Example Notebooks
- `examples/research/memory_effectiveness.ipynb`
- `examples/research/reasoning_analysis.ipynb`
- `examples/research/cost_optimization.ipynb`

### Support
- GitHub Issues: [rae-agentic-memory/issues](https://github.com/your-org/rae-agentic-memory/issues)
- Research Community: [Discord](https://discord.gg/rae-research)

---

## Citation

If you use RAE telemetry data in your research, please cite:

```bibtex
@software{rae_telemetry_2025,
  title = {RAE Telemetry Schema: Standardized Observability for Agentic AI Systems},
  author = {RAE Team},
  year = {2025},
  version = {1.0},
  url = {https://github.com/your-org/rae-agentic-memory}
}
```

---

**Happy Researching! 🔬**

For questions or contributions, please open an issue or join our research community.
