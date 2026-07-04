# RAE Cost Controller - Enterprise Budget Management & Token Tracking

**Version**: 3.0
**Status**: Production-Ready
**Last Updated**: 2025-01-22

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Database Schema](#database-schema)
4. [Components](#components)
5. [Request Flow](#request-flow)
6. [Configuration](#configuration)
7. [Monitoring & Metrics](#monitoring--metrics)
8. [API Reference](#api-reference)
9. [Examples](#examples)
10. [Troubleshooting](#troubleshooting)

---

## Overview

The RAE Cost Controller is an enterprise-grade system for tracking, managing, and enforcing budgets for LLM API usage. It provides:

- **Comprehensive Cost Tracking**: Track USD costs and token usage across all LLM providers
- **Budget Enforcement**: Daily and monthly limits for both USD and tokens
- **Complete Audit Trail**: Every LLM call logged to `cost_logs` table with full metadata
- **Multi-Provider Support**: OpenAI, Anthropic, Google, Ollama
- **Real-time Monitoring**: 8 Prometheus metrics for observability
- **Cost Validation**: Automatic correction when LLM providers return $0.00

### Key Features

✅ **Token Tracking** - Track input/output tokens separately
✅ **Dual Limits** - Enforce both USD and token budgets
✅ **Automatic Resets** - Daily/monthly counters reset via database triggers
✅ **Audit Logging** - Complete cost_logs table for governance
✅ **Cache Tracking** - Calculate cost savings from cache hits
✅ **Prometheus Metrics** - 8 metrics for comprehensive observability
✅ **Multi-Tenant** - Row-Level Security (RLS) for tenant isolation
✅ **Dry-Run Mode** - Test without budget enforcement

---

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Client Request                              │
│                  (with X-Dry-Run header)                         │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│               CostGuardMiddleware (cost_guard.py)               │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 1. PRE-EXECUTION: Budget Check                            │  │
│  │    - Extract model/provider from request                  │  │
│  │    - Estimate cost and tokens                             │  │
│  │    - Check budget limits (USD + tokens)                   │  │
│  │    - Track rejections in Prometheus                       │  │
│  └───────────────────────────────────────────────────────────┘  │
│                            │                                     │
│                            ▼                                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 2. EXECUTION: Call LLM API                                │  │
│  │    - Execute actual LLM call                              │  │
│  └───────────────────────────────────────────────────────────┘  │
│                            │                                     │
│                            ▼                                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 3. POST-EXECUTION: Cost Tracking                          │  │
│  │    - Extract actual tokens from response                  │  │
│  │    - Calculate cost using cost_controller                 │  │
│  │    - Validate LLM-reported cost (fix $0.00 bug)          │  │
│  │    - Log to cost_logs table                               │  │
│  │    - Increment budget usage                               │  │
│  │    - Update Prometheus metrics                            │  │
│  └───────────────────────────────────────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
        ┌──────────────┬────────────────┬──────────────────┐
        │              │                │                  │
        ▼              ▼                ▼                  ▼
┌────────────────┐ ┌──────────┐ ┌─────────────────┐ ┌──────────┐
│ cost_controller│ │ budgets  │ │   cost_logs     │ │Prometheus│
│  (calculate)   │ │  table   │ │     table       │ │ Metrics  │
└────────────────┘ └──────────┘ └─────────────────┘ └──────────┘
```

### Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                      LLM API Call                                │
└──────────────┬───────────────────────────────────────────────────┘
               │
               ▼
       ┏━━━━━━━━━━━━━━━━┓
       ┃ Cost Controller ┃
       ┃  calculate_cost()┃
       ┗━━━━━━┬━━━━━━━━━━┛
               │
               ├─────────────────────────────────┐
               │                                 │
               ▼                                 ▼
    ┌──────────────────┐              ┌──────────────────┐
    │   cost_model.py  │              │  BudgetService   │
    │ (pricing data)   │              │  check_budget()  │
    └──────────────────┘              └─────────┬────────┘
                                                  │
                                                  ▼
                                       ┌──────────────────┐
                                       │  budgets table   │
                                       │  (daily/monthly) │
                                       └──────────────────┘
                                                  │
                                                  ▼
                                       ┌──────────────────┐
                                       │ increment_usage()│
                                       └──────────────────┘
                                                  │
                                                  ▼
                                       ┌──────────────────┐
                                       │   cost_logs      │
                                       │ (audit trail)    │
                                       └──────────────────┘
```

---

## Database Schema

### `budgets` Table

Tracks cost and token budgets per tenant/project with daily and monthly limits.

```sql
CREATE TABLE budgets (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(255) NOT NULL,
    project_id VARCHAR(255) NOT NULL,

    -- USD Cost Limits
    daily_limit_usd DECIMAL(10, 4),
    monthly_limit_usd DECIMAL(10, 4),

    -- USD Usage Tracking
    daily_usage_usd DECIMAL(10, 4) DEFAULT 0.0,
    monthly_usage_usd DECIMAL(10, 4) DEFAULT 0.0,

    -- Token Limits
    daily_tokens_limit BIGINT,
    monthly_tokens_limit BIGINT,

    -- Token Usage Tracking
    daily_tokens_used BIGINT DEFAULT 0,
    monthly_tokens_used BIGINT DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_usage_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_token_update_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_daily_reset TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_monthly_reset TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE (tenant_id, project_id)
);
```

**Automatic Resets**: Database trigger `reset_budget_counters()` automatically resets daily counters at midnight and monthly counters on the 1st of each month.

### `cost_logs` Table

Complete audit log of all LLM API calls with detailed token and cost tracking.

```sql
CREATE TABLE cost_logs (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(255) NOT NULL,
    project_id VARCHAR(255) NOT NULL,

    -- LLM Call Metadata
    model VARCHAR(255) NOT NULL,
    provider VARCHAR(100) NOT NULL,
    operation VARCHAR(100) NOT NULL,

    -- Token Tracking
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    total_tokens INTEGER GENERATED ALWAYS AS (input_tokens + output_tokens) STORED,

    -- Cost Tracking (per million tokens)
    input_cost_per_million DECIMAL(10, 4) NOT NULL,
    output_cost_per_million DECIMAL(10, 4) NOT NULL,
    total_cost_usd DECIMAL(10, 6) NOT NULL,

    -- Cache Tracking
    cache_hit BOOLEAN DEFAULT FALSE,
    cache_tokens_saved INTEGER DEFAULT 0,

    -- Request Context
    request_id VARCHAR(255),
    user_id VARCHAR(255),

    -- Performance
    latency_ms INTEGER,
    error BOOLEAN DEFAULT FALSE,
    error_message TEXT,

    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

---

## Components

### 1. Cost Controller (`cost_controller.py`)

**Purpose**: Unified cost calculation for all LLM providers.

**Key Functions**:

- `calculate_cost(model, input_tokens, output_tokens, cache_hit)` → Cost breakdown
- `estimate_cost(model, est_input, est_output)` → Pre-flight estimation
- `get_model_rates(model)` → Pricing information
- `calculate_cache_savings(model, tokens_saved)` → ROI analysis
- `validate_cost_calculation()` → Detect pricing mismatches

**Features**:
- Replaces litellm.completion_cost() which returns $0.00
- Supports all providers: OpenAI, Anthropic, Google, Ollama
- Logs warnings for unknown models
- Returns detailed cost breakdown with per-million rates

### 2. Budget Service (`budget_service.py`)

**Purpose**: Budget enforcement and usage tracking.

**Key Functions**:

- `check_budget(pool, tenant_id, project_id, cost_usd, tokens)` → Raises HTTPException(402) if exceeded
- `increment_usage(pool, tenant_id, project_id, BudgetUsageIncrement)` → Updates budgets table
- `get_budget_status(pool, tenant_id, project_id)` → Returns budget status with percentages
- `set_budget_limits(pool, tenant_id, project_id, ...)` → Admin configuration

**Models**:

```python
class Budget(BaseModel):
    id: str
    tenant_id: str
    project_id: str
    monthly_limit_usd: Optional[float]
    daily_limit_usd: Optional[float]
    monthly_usage_usd: float
    daily_usage_usd: float
    monthly_tokens_limit: Optional[int]
    daily_tokens_limit: Optional[int]
    monthly_tokens_used: int
    daily_tokens_used: int
    # ... timestamps

class BudgetUsageIncrement(BaseModel):
    cost_usd: float
    input_tokens: int
    output_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens
```

### 3. Cost Logs Repository (`cost_logs_repository.py`)

**Purpose**: Audit logging and statistics.

**Key Functions**:

- `log_llm_call(pool, LogLLMCallParams)` → Inserts cost log entry
- `get_cost_statistics(pool, tenant, project, start, end)` → Aggregated stats
- `get_daily_cost(pool, tenant, project)` → Today's cost
- `get_monthly_cost(pool, tenant, project)` → This month's cost
- `get_model_breakdown(pool, tenant, project, start, end)` → Per-model costs
- `get_cache_savings(pool, tenant, project, start, end)` → Cache ROI

**Models**:

```python
class LogLLMCallParams(BaseModel):
    tenant_id: str
    project_id: str
    model: str
    provider: str
    operation: str
    input_tokens: int
    output_tokens: int
    input_cost_per_million: float
    output_cost_per_million: float
    total_cost_usd: float
    cache_hit: bool = False
    cache_tokens_saved: int = 0
    request_id: Optional[str] = None
    # ...
```

### 4. Cost Guard Middleware (`cost_guard.py`)

**Purpose**: Intercept all LLM calls for budget enforcement and logging.

**Features**:
- Pre-flight budget checks (USD + tokens)
- Post-execution cost tracking
- Audit logging to cost_logs table
- Automatic cost calculation if LLM returns $0.00
- Dry-run mode via `X-Dry-Run: true` header
- Comprehensive Prometheus metrics

**Decorator Usage**:

```python
@cost_guard()
async def agent_execute(self, request: AgentExecuteRequest):
    # Your LLM call here
    return response
```

---

## Request Flow

### Normal Request Flow

```
1. Client Request
   └─> POST /api/v1/agent/execute
       Headers: X-Request-ID: abc-123
       Body: { tenant_id, project, query, model, ... }

2. CostGuardMiddleware - PRE-EXECUTION
   ├─> Extract model info (model, provider, operation)
   ├─> Estimate cost: estimate_cost(model, ~2000 tokens)
   │   └─> cost_controller.calculate_cost()
   │       └─> cost_model.get_model_cost(model)
   ├─> Check budget: budget_service.check_budget()
   │   ├─> Query budgets table
   │   ├─> Compare projected usage vs limits
   │   └─> Raise HTTPException(402) if exceeded
   │       └─> Increment rae_cost_budget_rejections_total
   └─> Budget check passed ✓

3. LLM API Call Execution
   └─> Call actual LLM API (OpenAI/Anthropic/etc)
       └─> Get response with tokens and cost

4. CostGuardMiddleware - POST-EXECUTION
   ├─> Extract actual tokens from response
   ├─> Calculate cost: cost_controller.calculate_cost()
   │   ├─> If LLM reported $0.00, use our calculation
   │   └─> Validate against LLM-reported cost
   ├─> Log to audit trail: cost_logs_repository.log_llm_call()
   │   └─> INSERT INTO cost_logs (...)
   ├─> Increment budget: budget_service.increment_usage()
   │   └─> UPDATE budgets SET daily_usage_usd += cost, ...
   └─> Update Prometheus metrics
       ├─> rae_cost_llm_total_usd.inc(cost)
       ├─> rae_cost_llm_tokens_used.inc(tokens)
       ├─> rae_cost_llm_calls_total.inc()
       ├─> rae_cost_tokens_per_call_histogram.observe(tokens)
       ├─> rae_cost_llm_daily_usd.set(daily_cost)
       └─> rae_cost_llm_monthly_usd.set(monthly_cost)

5. Return Response
   └─> Return LLM response to client
```

### Budget Exceeded Flow

```
1. Client Request
   └─> POST /api/v1/agent/execute

2. CostGuardMiddleware - PRE-EXECUTION
   ├─> Estimate cost: $0.015
   ├─> Check budget: budget_service.check_budget()
   │   ├─> Current daily usage: $9.99
   │   ├─> Daily limit: $10.00
   │   ├─> Projected: $9.99 + $0.015 = $10.005 > $10.00
   │   └─> BUDGET EXCEEDED! 🚫
   └─> Raise HTTPException(402)
       ├─> Increment rae_cost_budget_rejections_total
       └─> Return detailed error:
           {
             "error": "daily_usd_budget_exceeded",
             "message": "Daily USD budget exceeded for project 'X'",
             "current_usage_usd": 9.99,
             "daily_limit_usd": 10.00,
             "requested_cost_usd": 0.015,
             "projected_usage_usd": 10.005,
             "available_usd": 0.01
           }

3. Return 402 Payment Required
   └─> Client receives detailed budget error
```

### Dry-Run Mode Flow

```
1. Client Request
   └─> POST /api/v1/agent/execute
       Headers: X-Dry-Run: true

2. CostGuardMiddleware - PRE-EXECUTION
   ├─> Detect dry-run mode
   └─> SKIP budget check (for testing) ⏭️

3. LLM API Call Execution
   └─> Execute normally

4. CostGuardMiddleware - POST-EXECUTION
   ├─> Calculate actual cost
   ├─> SKIP audit logging (dry-run)
   ├─> SKIP budget increment (dry-run)
   ├─> SKIP Prometheus metrics (dry-run)
   └─> Log: "Dry Run: Estimated cost is $X.XX"

5. Return Response
   └─> Normal response (without budget enforcement)
```

---

## Configuration

### 1. Setting Budget Limits

Use the `set_budget_limits()` function to configure limits:

```python
from apps.memory_api.services import budget_service

# Set USD limits
await budget_service.set_budget_limits(
    pool,
    tenant_id="acme-corp",
    project_id="production",
    daily_limit_usd=50.00,      # $50/day
    monthly_limit_usd=1000.00   # $1000/month
)

# Set token limits
await budget_service.set_budget_limits(
    pool,
    tenant_id="acme-corp",
    project_id="production",
    daily_tokens_limit=5_000_000,      # 5M tokens/day
    monthly_tokens_limit=100_000_000   # 100M tokens/month
)

# Set both
await budget_service.set_budget_limits(
    pool,
    tenant_id="acme-corp",
    project_id="production",
    daily_limit_usd=50.00,
    monthly_limit_usd=1000.00,
    daily_tokens_limit=5_000_000,
    monthly_tokens_limit=100_000_000
)

# Remove limits (set to None for unlimited)
await budget_service.set_budget_limits(
    pool,
    tenant_id="acme-corp",
    project_id="sandbox",
    daily_limit_usd=None,    # Unlimited
    monthly_limit_usd=None   # Unlimited
)
```

### 2. Adding New Models to Cost Database

Edit `apps/memory_api/cost_model.py`:

```python
MODEL_COSTS = {
    # Add your model here (costs per million tokens)
    "gpt-5": {"input": 80.0, "output": 160.0},
    "claude-opus-5": {"input": 20.0, "output": 100.0},

    # Existing models...
    "gpt-4o-mini": {"input": 0.5, "output": 1.5},
    "claude-3.5-sonnet-20240620": {"input": 3.0, "output": 15.0},

    # Local models (free)
    "ollama/llama2": {"input": 0.0, "output": 0.0},
}
```

**Important**: If a model is not in `MODEL_COSTS`, the cost will be calculated as $0.00 and a warning will be logged.

### 3. Environment Variables

```bash
# PostgreSQL connection (for budgets and cost_logs)
DATABASE_URL=postgresql://user:pass@localhost:5432/rae

# Optional: Default budget limits for new tenants
DEFAULT_DAILY_LIMIT_USD=10.0
DEFAULT_MONTHLY_LIMIT_USD=100.0
DEFAULT_DAILY_TOKENS_LIMIT=1000000
DEFAULT_MONTHLY_TOKENS_LIMIT=10000000
```

---

## Monitoring & Metrics

### Prometheus Metrics

The Cost Controller exposes 8 enterprise-grade metrics:

#### 1. `rae_cost_llm_total_usd` (Counter)

Total cumulative LLM costs in USD.

**Labels**: `tenant_id`, `project`, `model`, `provider`

**Query Examples**:

```promql
# Total cost across all tenants
sum(rae_cost_llm_total_usd)

# Cost per tenant
sum by (tenant_id) (rae_cost_llm_total_usd)

# Cost per model
sum by (model) (rae_cost_llm_total_usd)

# Most expensive tenant
topk(10, sum by (tenant_id) (rae_cost_llm_total_usd))
```

#### 2. `rae_cost_llm_daily_usd` (Gauge)

Current daily LLM costs in USD (resets at midnight UTC).

**Labels**: `tenant_id`, `project`

**Query Examples**:

```promql
# Current daily cost for tenant
rae_cost_llm_daily_usd{tenant_id="acme-corp"}

# Tenants approaching daily limit (>90%)
(rae_cost_llm_daily_usd / on(tenant_id, project) budgets_daily_limit_usd) > 0.9
```

#### 3. `rae_cost_llm_monthly_usd` (Gauge)

Current monthly LLM costs in USD (resets on 1st of month).

**Labels**: `tenant_id`, `project`

**Query Examples**:

```promql
# Current monthly cost for tenant
rae_cost_llm_monthly_usd{tenant_id="acme-corp"}

# Monthly burn rate
rate(rae_cost_llm_monthly_usd[7d])
```

#### 4. `rae_cost_llm_tokens_used` (Counter)

Total cumulative tokens used (input + output).

**Labels**: `tenant_id`, `project`, `model`, `provider`

**Query Examples**:

```promql
# Total tokens across all tenants
sum(rae_cost_llm_tokens_used)

# Tokens per model
sum by (model) (rae_cost_llm_tokens_used)

# Most token-intensive tenant
topk(10, sum by (tenant_id) (rae_cost_llm_tokens_used))
```

#### 5. `rae_cost_cache_saved_usd` (Counter)

Estimated cost savings from cache hits in USD.

**Labels**: `tenant_id`, `project`

**Query Examples**:

```promql
# Total cache savings
sum(rae_cost_cache_saved_usd)

# Cache ROI per tenant
sum by (tenant_id) (rae_cost_cache_saved_usd)

# Cache savings rate (savings / total cost)
sum(rae_cost_cache_saved_usd) / sum(rae_cost_llm_total_usd)
```

#### 6. `rae_cost_budget_rejections_total` (Counter)

Total number of requests rejected due to budget limits.

**Labels**: `tenant_id`, `project`, `limit_type`

**Limit Types**: `daily_usd`, `monthly_usd`, `daily_tokens`, `monthly_tokens`

**Query Examples**:

```promql
# Total rejections
sum(rae_cost_budget_rejections_total)

# Rejections by limit type
sum by (limit_type) (rae_cost_budget_rejections_total)

# Tenants with most rejections
topk(10, sum by (tenant_id) (rae_cost_budget_rejections_total))

# Rejection rate
rate(rae_cost_budget_rejections_total[5m])
```

#### 7. `rae_cost_llm_calls_total` (Counter)

Total number of LLM API calls.

**Labels**: `tenant_id`, `project`, `model`, `provider`, `operation`

**Operations**: `query`, `reflection`, `embedding`, `entity_extraction`, etc.

**Query Examples**:

```promql
# Total API calls
sum(rae_cost_llm_calls_total)

# Calls per operation
sum by (operation) (rae_cost_llm_calls_total)

# Call rate
rate(rae_cost_llm_calls_total[5m])

# Most active tenant
topk(10, sum by (tenant_id) (rae_cost_llm_calls_total))
```

#### 8. `rae_cost_tokens_per_call` (Histogram)

Distribution of tokens used per LLM call.

**Labels**: `model`, `provider`

**Buckets**: 100, 500, 1K, 2K, 5K, 10K, 20K, 50K, 100K, 200K tokens

**Query Examples**:

```promql
# Average tokens per call
histogram_quantile(0.5, rae_cost_tokens_per_call_bucket)

# 95th percentile tokens per call
histogram_quantile(0.95, rae_cost_tokens_per_call_bucket)

# Calls with >10K tokens
sum(rae_cost_tokens_per_call_bucket{le="20000"}) - sum(rae_cost_tokens_per_call_bucket{le="10000"})
```

### Grafana Dashboard

**Recommended Panels**:

1. **Cost Overview** - Total spend, daily trend, monthly projection
2. **Token Usage** - Total tokens, tokens by model, tokens per call histogram
3. **Budget Health** - Current usage vs limits, projected overage alerts
4. **Cache Performance** - Cache hit rate, cost savings, ROI
5. **API Calls** - Call rate, calls by operation, error rate
6. **Budget Rejections** - Rejection count, rejection rate, limit type breakdown
7. **Model Breakdown** - Cost per model, tokens per model, calls per model
8. **Tenant Leaderboard** - Top 10 by cost, tokens, and calls

**Alert Rules**:

```yaml
# Alert when tenant approaches daily budget
- alert: DailyBudgetNearLimit
  expr: (rae_cost_llm_daily_usd / budgets_daily_limit_usd) > 0.9
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Tenant {{ $labels.tenant_id }} approaching daily budget"

# Alert on budget rejections
- alert: BudgetRejectionsSpike
  expr: rate(rae_cost_budget_rejections_total[5m]) > 1
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "High rate of budget rejections for {{ $labels.tenant_id }}"

# Alert on cost spike
- alert: UnexpectedCostIncrease
  expr: rate(rae_cost_llm_total_usd[1h]) > 10
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "Unusual cost increase detected"
```

---

## API Reference

### Cost Controller API

#### `calculate_cost(model_name, input_tokens, output_tokens, cache_hit=False)`

**Purpose**: Calculate cost for an LLM API call.

**Parameters**:
- `model_name` (str): Full model identifier (e.g., "gpt-4o-mini")
- `input_tokens` (int): Number of input tokens consumed
- `output_tokens` (int): Number of output tokens generated
- `cache_hit` (bool): Whether this was a cache hit (default False)

**Returns**: Dictionary with:

```python
{
    "total_cost_usd": 0.001500,
    "input_cost_per_million": 0.5,
    "output_cost_per_million": 1.5,
    "input_tokens": 1500,
    "output_tokens": 500,
    "total_tokens": 2000,
    "model_name": "gpt-4o-mini",
    "cache_hit": False,
    "cost_known": True
}
```

**Example**:

```python
from apps.memory_api.services.cost_controller import calculate_cost

cost_info = calculate_cost("gpt-4o-mini", 1500, 500)
print(f"Cost: ${cost_info['total_cost_usd']:.6f}")  # $0.001500
```

#### `estimate_cost(model_name, estimated_input_tokens, estimated_output_tokens)`

**Purpose**: Estimate cost for pre-flight budget checks.

**Returns**: float (total cost in USD)

**Example**:

```python
from apps.memory_api.services.cost_controller import estimate_cost

estimated = estimate_cost("gpt-4o", 2000, 1000)
if estimated > budget_remaining:
    raise HTTPException(402, "Budget exceeded")
```

### Budget Service API

#### `check_budget(pool, tenant_id, project_id, cost_usd, tokens)`

**Purpose**: Check if a new cost is within budget.

**Raises**: `HTTPException(402)` if budget exceeded with detailed error message.

**Example**:

```python
from apps.memory_api.services import budget_service

await budget_service.check_budget(
    pool,
    "acme-corp",
    "production",
    cost_usd=0.015,
    tokens=2000
)
```

**Error Response (402)**:

```json
{
  "error": "daily_usd_budget_exceeded",
  "message": "Daily USD budget exceeded for project 'production'",
  "current_usage_usd": 9.99,
  "daily_limit_usd": 10.00,
  "requested_cost_usd": 0.015,
  "projected_usage_usd": 10.005,
  "available_usd": 0.01
}
```

#### `increment_usage(pool, tenant_id, project_id, BudgetUsageIncrement)`

**Purpose**: Increment daily and monthly usage for both USD and tokens.

**Example**:

```python
from apps.memory_api.services.budget_service import BudgetUsageIncrement

await budget_service.increment_usage(
    pool,
    "acme-corp",
    "production",
    BudgetUsageIncrement(
        cost_usd=0.015,
        input_tokens=1500,
        output_tokens=500
    )
)
```

### Cost Logs Repository API

#### `log_llm_call(pool, LogLLMCallParams)`

**Purpose**: Log an LLM API call to the audit trail.

**Returns**: UUID of the created log entry.

**Example**:

```python
from apps.memory_api.repositories.cost_logs_repository import LogLLMCallParams
from apps.memory_api.repositories import cost_logs_repository

log_id = await cost_logs_repository.log_llm_call(
    pool,
    LogLLMCallParams(
        tenant_id="acme-corp",
        project_id="production",
        model="gpt-4o-mini",
        provider="openai",
        operation="query",
        input_tokens=1500,
        output_tokens=500,
        input_cost_per_million=0.5,
        output_cost_per_million=1.5,
        total_cost_usd=0.001500,
        cache_hit=False,
        request_id="abc-123"
    )
)
```

#### `get_cost_statistics(pool, tenant_id, project_id, period_start, period_end)`

**Purpose**: Get aggregated cost statistics for a time period.

**Returns**: `CostStatistics` object.

**Example**:

```python
from datetime import datetime, timedelta

stats = await cost_logs_repository.get_cost_statistics(
    pool,
    "acme-corp",
    "production",
    datetime.now() - timedelta(days=7),
    datetime.now()
)

print(f"Total cost: ${stats.total_cost_usd:.2f}")
print(f"Total calls: {stats.total_calls}")
print(f"Cache hit rate: {stats.cache_hit_rate:.1f}%")
```

---

## Examples

### Example 1: Basic LLM Call with Cost Tracking

```python
from fastapi import FastAPI, Request
from apps.memory_api.middleware.cost_guard import cost_guard
from apps.memory_api.models import AgentExecuteRequest, AgentExecuteResponse

app = FastAPI()

@app.post("/api/v1/agent/execute")
@cost_guard()
async def agent_execute(
    request: Request,
    body: AgentExecuteRequest
):
    # Your LLM call here
    response = await call_llm(body)
    return response
```

**What Happens**:
1. Pre-flight budget check
2. LLM call execution
3. Automatic cost calculation
4. Audit logging to cost_logs
5. Budget increment
6. Prometheus metrics update

### Example 2: Query Budget Status

```python
from apps.memory_api.services import budget_service

# Get current budget status
status = await budget_service.get_budget_status(
    pool,
    "acme-corp",
    "production"
)

print(f"Daily usage: ${status['usd']['daily']['usage']:.2f} / ${status['usd']['daily']['limit']:.2f}")
print(f"Daily tokens: {status['tokens']['daily']['usage']} / {status['tokens']['daily']['limit']}")
print(f"Daily USD percentage: {status['usd']['daily']['percentage']:.1f}%")
print(f"Monthly cost: ${status['usd']['monthly']['usage']:.2f}")
```

**Output**:

```
Daily usage: $9.75 / $10.00
Daily tokens: 4500000 / 5000000
Daily USD percentage: 97.5%
Monthly cost: $287.50
```

### Example 3: Analyze Costs by Model

```python
from datetime import datetime, timedelta
from apps.memory_api.repositories import cost_logs_repository

# Get model breakdown for last 30 days
breakdowns = await cost_logs_repository.get_model_breakdown(
    pool,
    "acme-corp",
    "production",
    datetime.now() - timedelta(days=30),
    datetime.now()
)

for breakdown in breakdowns:
    print(f"{breakdown.model} ({breakdown.provider}):")
    print(f"  Calls: {breakdown.total_calls}")
    print(f"  Cost: ${breakdown.total_cost_usd:.2f}")
    print(f"  Avg/call: ${breakdown.avg_cost_per_call:.4f}")
    print()
```

**Output**:

```
gpt-4o-mini (openai):
  Calls: 15234
  Cost: $245.67
  Avg/call: $0.0161

claude-3.5-sonnet-20240620 (anthropic):
  Calls: 3421
  Cost: $187.43
  Avg/call: $0.0548

gemini-1.5-pro-002 (google):
  Calls: 892
  Cost: $98.21
  Avg/call: $0.1101
```

### Example 4: Dry-Run Mode Testing

```bash
# Test without budget enforcement
curl -X POST http://localhost:8000/api/v1/agent/execute \
  -H "Content-Type: application/json" \
  -H "X-Dry-Run: true" \
  -d '{
    "tenant_id": "acme-corp",
    "project": "production",
    "query": "What is the capital of France?",
    "model": "gpt-4o-mini"
  }'
```

**Logs**:

```
cost_guard_pre_execution tenant_id=acme-corp dry_run=True
cost_guard_estimate estimated_cost_usd=0.015 estimated_tokens=3000
[SKIPPED budget check - dry run mode]
cost_guard_post_execution actual_cost_usd=0.012 tokens=2100
cost_guard_dry_run_complete estimated_cost=0.012 message="Dry Run: Estimated cost is $0.012000"
```

### Example 5: Setting Up Budgets for New Tenant

```python
from apps.memory_api.services import budget_service

# Create budget for new tenant
await budget_service.set_budget_limits(
    pool,
    tenant_id="new-startup",
    project_id="mvp",
    daily_limit_usd=5.00,        # $5/day for MVP testing
    monthly_limit_usd=100.00,    # $100/month
    daily_tokens_limit=1_000_000,    # 1M tokens/day
    monthly_tokens_limit=20_000_000  # 20M tokens/month
)

# Verify budget created
status = await budget_service.get_budget_status(pool, "new-startup", "mvp")
print(f"Budget created successfully!")
print(f"Daily limit: ${status['usd']['daily']['limit']}")
print(f"Monthly limit: ${status['usd']['monthly']['limit']}")
```

---

## Troubleshooting

### Problem 1: Cost is Always $0.00

**Symptom**: `total_cost_usd` is always 0 in cost_logs.

**Cause**: Model not in `cost_model.py` pricing database.

**Solution**:

1. Check logs for warning:
   ```
   unknown_model_cost model_name="custom-model-123"
   ```

2. Add model to `apps/memory_api/cost_model.py`:
   ```python
   MODEL_COSTS = {
       "custom-model-123": {"input": 1.0, "output": 2.0},
       # ...
   }
   ```

3. Restart API server.

### Problem 2: Budget Never Exceeded

**Symptom**: Requests succeed even when budget should be exceeded.

**Cause**: Budget limits not set (NULL = unlimited).

**Solution**:

```python
# Check current limits
status = await budget_service.get_budget_status(pool, tenant_id, project_id)
print(status['usd']['daily']['limit'])  # Should NOT be None

# Set limits
await budget_service.set_budget_limits(
    pool, tenant_id, project_id,
    daily_limit_usd=10.00,
    monthly_limit_usd=100.00
)
```

### Problem 3: Database Trigger Not Working

**Symptom**: Daily/monthly counters not resetting.

**Cause**: Trigger `reset_budget_counters()` not created or failing.

**Solution**:

1. Check trigger exists:
   ```sql
   SELECT tgname FROM pg_trigger WHERE tgname = 'trigger_reset_budget_counters';
   ```

2. If missing, re-run schema:
   ```bash
   psql -U rae -d rae -f infra/postgres/ddl/005_cost_control.sql
   ```

3. Test trigger manually:
   ```sql
   -- Simulate day boundary
   UPDATE budgets SET last_daily_reset = NOW() - INTERVAL '2 days' WHERE tenant_id = 'test';

   -- Trigger should reset daily counters
   UPDATE budgets SET last_usage_at = NOW() WHERE tenant_id = 'test';

   -- Check reset occurred
   SELECT daily_usage_usd, daily_tokens_used FROM budgets WHERE tenant_id = 'test';
   ```

### Problem 4: Prometheus Metrics Not Appearing

**Symptom**: Metrics endpoint `/metrics` doesn't show `rae_cost_*` metrics.

**Cause**: Metrics not imported or never incremented.

**Solution**:

1. Check metrics are imported in `metrics.py`:
   ```python
   from prometheus_client import Counter, Gauge, Histogram

   rae_cost_llm_total_usd = Counter(...)
   ```

2. Check middleware imports metrics:
   ```python
   from apps.memory_api.metrics import rae_cost_llm_total_usd, ...
   ```

3. Make at least one LLM call to initialize metrics.

4. Verify at `/metrics`:
   ```bash
   curl http://localhost:8000/metrics | grep rae_cost
   ```

### Problem 5: High Budget Rejection Rate

**Symptom**: Many requests failing with 402 status.

**Cause**: Budget limits too low for usage pattern.

**Solution**:

1. Analyze rejection patterns:
   ```promql
   sum by (limit_type) (rae_cost_budget_rejections_total)
   ```

2. Check current usage:
   ```python
   status = await budget_service.get_budget_status(pool, tenant_id, project_id)
   print(f"Daily: ${status['usd']['daily']['usage']:.2f} / ${status['usd']['daily']['limit']:.2f}")
   ```

3. Increase limits:
   ```python
   await budget_service.set_budget_limits(
       pool, tenant_id, project_id,
       daily_limit_usd=50.00,  # Increased from $10
       monthly_limit_usd=1000.00
   )
   ```

### Problem 6: Cost Mismatch Between LLM and Our Calculation

**Symptom**: Warning logs:
```
cost_guard_cost_mismatch our_cost=0.015 llm_reported=0.018
```

**Cause**: LLM provider changed pricing or our `cost_model.py` is outdated.

**Solution**:

1. Verify current pricing from provider documentation.

2. Update `cost_model.py` with correct rates:
   ```python
   "gpt-4o-mini": {"input": 0.5, "output": 1.5},  # Update these
   ```

3. Our calculation takes precedence (more reliable than litellm).

---

## Appendix: Cost Model Reference

### OpenAI Pricing (as of 2025)

| Model | Input ($/M tokens) | Output ($/M tokens) |
|-------|-------------------|---------------------|
| gpt-4o | $5.00 | $15.00 |
| gpt-4o-mini | $0.50 | $1.50 |
| gpt-3.5-turbo | $0.50 | $1.50 |
| o1 | $20.00 | $40.00 |
| o1-mini | $5.00 | $15.00 |

### Anthropic Pricing

| Model | Input ($/M tokens) | Output ($/M tokens) |
|-------|-------------------|---------------------|
| claude-sonnet-4-5 | $3.00 | $15.00 |
| claude-opus-4 | $15.00 | $75.00 |
| claude-haiku-4-5 | $0.25 | $1.25 |
| claude-3.5-sonnet | $3.00 | $15.00 |

### Google Pricing

| Model | Input ($/M tokens) | Output ($/M tokens) |
|-------|-------------------|---------------------|
| gemini-1.5-pro-002 | $2.00 | $6.00 |
| gemini-pro | $0.50 | $1.50 |

### Ollama / Local Models

| Model | Input ($/M tokens) | Output ($/M tokens) |
|-------|-------------------|---------------------|
| Any ollama/* model | $0.00 | $0.00 |
| phi-3 | $0.00 | $0.00 |

---

## Summary

The RAE Cost Controller provides enterprise-grade budget management and cost tracking for LLM API usage. Key features:

✅ **Comprehensive Tracking** - USD + tokens, daily + monthly
✅ **Budget Enforcement** - Pre-flight checks with detailed errors
✅ **Complete Audit Trail** - Every LLM call logged with metadata
✅ **Automatic Cost Calculation** - Fixes litellm $0.00 bug
✅ **Multi-Provider Support** - OpenAI, Anthropic, Google, Ollama
✅ **Rich Observability** - 8 Prometheus metrics for monitoring
✅ **Multi-Tenant** - RLS for data isolation
✅ **Production-Ready** - Database triggers, error handling, logging

**Next Steps**:

1. Set up budgets for your tenants
2. Add your models to `cost_model.py`
3. Configure Prometheus/Grafana dashboards
4. Set up budget limit alerts
5. Monitor via `/metrics` endpoint

**Questions or Issues?**

- GitHub Issues: https://github.com/dreamsoft-pro/RAE-agentic-memory/issues
- Documentation: https://github.com/dreamsoft-pro/RAE-agentic-memory/tree/main/docs

---

**End of Documentation**
