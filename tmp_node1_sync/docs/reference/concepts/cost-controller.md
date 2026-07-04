# Cost Controller

RAE includes a sophisticated cost tracking and budget management system to help you control LLM API expenses.

## Table of Contents

- [Overview](#overview)
- [How It Works](#how-it-works)
- [Cost Tracking](#cost-tracking)
- [Budget Management](#budget-management)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)
- [Best Practices](#best-practices)

## Overview

The Cost Controller provides:

- **Real-time cost tracking** for LLM API calls
- **Budget limits** (daily and monthly)
- **Automatic budget enforcement** with HTTP 402 responses
- **Multi-tenant cost isolation**
- **Detailed usage analytics**
- **Support for all major LLM providers**

## How It Works

### Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Client Request                      │
└─────────────────┬───────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────┐
│            Cost Guard Middleware                     │
│  - Intercepts LLM calls                             │
│  - Checks budget BEFORE call                        │
└─────────────────┬───────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────┐
│               Budget Service                         │
│  - Validate against daily/monthly limits            │
│  - Return 402 if exceeded                           │
└─────────────────┬───────────────────────────────────┘
                  │ ✓ Budget OK
                  ▼
┌─────────────────────────────────────────────────────┐
│                  LLM Call                            │
│  (OpenAI, Anthropic, Gemini, etc.)                  │
└─────────────────┬───────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────┐
│            Cost Calculation                          │
│  - Count input/output tokens                        │
│  - Calculate actual cost                            │
└─────────────────┬───────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────┐
│           Increment Usage Counters                   │
│  - Update daily_usage                               │
│  - Update monthly_usage                             │
│  - Store in database                                │
└─────────────────────────────────────────────────────┘
```

## Cost Tracking

### Supported Models

RAE tracks costs for all major LLM providers:

**OpenAI:**
- GPT-4o: $5.00 / $15.00 per million tokens (input/output)
- GPT-4o-mini: $0.50 / $1.50 per million tokens
- GPT-4: $30.00 / $60.00 per million tokens
- GPT-3.5-turbo: $0.50 / $1.50 per million tokens
- o1 models: $20.00 / $40.00 per million tokens

**Anthropic:**
- Claude Opus 4: $15.00 / $75.00 per million tokens
- Claude Sonnet 3.5: $3.00 / $15.00 per million tokens
- Claude Haiku 3: $0.25 / $1.25 per million tokens

**Google:**
- Gemini 1.5 Pro: $2.00 / $6.00 per million tokens
- Gemini Pro: $0.50 / $1.50 per million tokens

**Local/Open Source:**
- Ollama models: $0.00 (free)
- Local models: $0.00 (free)

### Cost Calculation

```python
def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """
    Calculate LLM API cost in USD
    """
    costs = get_model_cost(model)

    input_cost = (input_tokens / 1_000_000) * costs["input"]
    output_cost = (output_tokens / 1_000_000) * costs["output"]

    return input_cost + output_cost
```

**Example:**
```python
# GPT-4o: 1000 input tokens, 500 output tokens
input_cost = (1000 / 1_000_000) * 5.00 = $0.005
output_cost = (500 / 1_000_000) * 15.00 = $0.0075
total = $0.0125
```

## Budget Management

### Budget Model

```python
class Budget:
    id: str
    tenant_id: str
    project_id: str
    monthly_limit: float | None  # USD
    monthly_usage: float          # USD
    daily_limit: float | None     # USD
    daily_usage: float            # USD
    last_usage_at: datetime
```

### Budget Enforcement

The system checks budgets **before** making LLM calls:

```python
async def check_budget(tenant_id: str, project_id: str, estimated_cost: float):
    """
    Raises HTTPException(402) if budget exceeded
    """
    budget = await get_budget(tenant_id, project_id)

    # Check daily limit
    if budget.daily_limit and (budget.daily_usage + estimated_cost) > budget.daily_limit:
        raise HTTPException(
            status_code=402,
            detail=f"Daily budget exceeded. Limit: ${budget.daily_limit}"
        )

    # Check monthly limit
    if budget.monthly_limit and (budget.monthly_usage + estimated_cost) > budget.monthly_limit:
        raise HTTPException(
            status_code=402,
            detail=f"Monthly budget exceeded. Limit: ${budget.monthly_limit}"
        )
```

### Automatic Reset

Budgets automatically reset:
- **Daily usage**: Resets at midnight
- **Monthly usage**: Resets on the 1st of each month

## Configuration

### Environment Variables

```env
# Enable cost tracking
ENABLE_COST_TRACKING=true

# Default budgets (optional)
DEFAULT_DAILY_LIMIT=10.00    # $10 per day
DEFAULT_MONTHLY_LIMIT=100.00 # $100 per month

# Alert thresholds
BUDGET_WARNING_THRESHOLD=0.8  # Warn at 80%
BUDGET_ALERT_EMAIL=admin@example.com
```

### Database Schema

```sql
CREATE TABLE budgets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    project_id UUID NOT NULL,
    monthly_limit DECIMAL(10, 2),
    monthly_usage DECIMAL(10, 2) DEFAULT 0,
    daily_limit DECIMAL(10, 2),
    daily_usage DECIMAL(10, 2) DEFAULT 0,
    last_usage_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(tenant_id, project_id)
);

-- Track individual costs
CREATE TABLE cost_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    project_id UUID NOT NULL,
    model TEXT NOT NULL,
    input_tokens INT NOT NULL,
    output_tokens INT NOT NULL,
    cost DECIMAL(10, 4) NOT NULL,
    operation TEXT,  -- 'reflection', 'query', 'embedding', etc.
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Usage Examples

### Setting Budgets via API

```bash
# Set monthly budget
curl -X PUT http://localhost:8000/v1/budgets \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: acme-corp" \
  -H "X-Project-ID: project-alpha" \
  -d '{
    "monthly_limit": 500.00,
    "daily_limit": 20.00
  }'
```

### Checking Current Usage

```bash
# Get budget status
curl http://localhost:8000/v1/budgets/current \
  -H "X-Tenant-ID: acme-corp" \
  -H "X-Project-ID: project-alpha"
```

**Response:**
```json
{
  "tenant_id": "acme-corp",
  "project_id": "project-alpha",
  "monthly_limit": 500.00,
  "monthly_usage": 123.45,
  "monthly_remaining": 376.55,
  "daily_limit": 20.00,
  "daily_usage": 3.21,
  "daily_remaining": 16.79,
  "usage_percentage": 24.7,
  "estimated_days_remaining": 11
}
```

### Handling Budget Errors

```python
from rae_memory_sdk import MemoryClient
from httpx import HTTPStatusError

client = MemoryClient(...)

try:
    result = await client.generate_reflection()
except HTTPStatusError as e:
    if e.response.status_code == 402:
        print("Budget exceeded! Please increase limits or wait for reset.")
        # Implement fallback logic:
        # - Use cached results
        # - Use cheaper model
        # - Queue for later processing
    else:
        raise
```

### Cost-Aware Model Selection

```python
def select_model_by_budget(remaining_budget: float, task_complexity: str) -> str:
    """
    Choose appropriate model based on remaining budget
    """
    if remaining_budget < 1.00:
        # Low budget: use cheapest models
        return "gpt-4o-mini" if task_complexity == "simple" else "claude-haiku-3"

    elif remaining_budget < 10.00:
        # Medium budget: balanced models
        return "gpt-4o-mini" if task_complexity == "simple" else "claude-sonnet-3.5"

    else:
        # High budget: premium models
        return "gpt-4o" if task_complexity == "simple" else "claude-opus-4"
```

## Best Practices

### 1. Set Realistic Limits

Calculate expected usage:
```
Daily operations:
- 100 memory stores × $0.0001 = $0.01
- 50 queries × $0.001 = $0.05
- 5 reflections × $0.05 = $0.25
Total: ~$0.31/day = ~$10/month
```

Set limits with 50% buffer:
```env
DEFAULT_DAILY_LIMIT=0.50
DEFAULT_MONTHLY_LIMIT=15.00
```

### 2. Monitor Usage Trends

```sql
-- Daily usage trend
SELECT
    DATE(created_at) as date,
    SUM(cost) as daily_cost,
    COUNT(*) as operations
FROM cost_logs
WHERE tenant_id = $1
GROUP BY DATE(created_at)
ORDER BY date DESC
LIMIT 30;
```

### 3. Implement Alerts

```python
async def check_budget_alerts(tenant_id: str, project_id: str):
    """
    Send alerts when approaching limits
    """
    budget = await get_budget(tenant_id, project_id)

    # Alert at 80% usage
    if budget.monthly_usage / budget.monthly_limit > 0.8:
        await send_alert(
            f"Warning: 80% of monthly budget used",
            tenant_id=tenant_id
        )

    # Alert at 95% usage
    if budget.monthly_usage / budget.monthly_limit > 0.95:
        await send_alert(
            f"CRITICAL: 95% of monthly budget used",
            tenant_id=tenant_id
        )
```

### 4. Use Caching Aggressively

Reduce costs by caching LLM responses:

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_cached_reflection(content_hash: str) -> str:
    """
    Cache reflection results to avoid duplicate LLM calls
    """
    # Check Redis cache
    cached = redis.get(f"reflection:{content_hash}")
    if cached:
        return cached

    # Generate if not cached
    reflection = llm.generate_reflection(content)
    redis.setex(f"reflection:{content_hash}", 86400, reflection)
    return reflection
```

### 5. Fallback Strategies

Implement graceful degradation:

```python
async def query_with_fallback(query: str) -> dict:
    """
    Try premium model, fallback to cheaper alternatives
    """
    try:
        # Try GPT-4o first
        return await query_memory(query, model="gpt-4o")
    except BudgetExceededError:
        # Fallback to GPT-4o-mini
        return await query_memory(query, model="gpt-4o-mini")
    except BudgetExceededError:
        # Final fallback: local model (free)
        return await query_memory(query, model="ollama/llama3")
```

### 6. Per-Tenant Pricing Tiers

```python
TIER_LIMITS = {
    "free": {
        "daily_limit": 0.50,
        "monthly_limit": 5.00
    },
    "pro": {
        "daily_limit": 5.00,
        "monthly_limit": 100.00
    },
    "enterprise": {
        "daily_limit": 50.00,
        "monthly_limit": 1000.00
    }
}
```

## Cost Optimization Tips

### 1. Use Smaller Models When Possible

```python
# For simple tasks
"gpt-4o-mini"      # $0.50/$1.50 per M tokens
"claude-haiku-3"   # $0.25/$1.25 per M tokens

# For complex reasoning
"gpt-4o"          # $5/$15 per M tokens
"claude-sonnet"   # $3/$15 per M tokens
```

### 2. Batch Operations

```python
# Bad: Individual calls
for memory in memories:
    await generate_embedding(memory.content)  # $0.0001 each

# Good: Batch call
embeddings = await generate_embeddings_batch([m.content for m in memories])
# Single API call = lower overhead
```

### 3. Optimize Prompts

- Remove unnecessary context
- Use shorter system prompts
- Cache common prompt templates

### 4. Use Local Models for Development

```env
# Development
RAE_LLM_BACKEND=ollama
RAE_LLM_MODEL_DEFAULT=llama3

# Production
RAE_LLM_BACKEND=openai
RAE_LLM_MODEL_DEFAULT=gpt-4o-mini
```

## Monitoring Dashboard

Track costs in Grafana:

```prometheus
# Prometheus metrics
rae_llm_cost_total{tenant="acme", model="gpt-4o"}
rae_llm_tokens_total{type="input", tenant="acme"}
rae_budget_remaining{tenant="acme", period="monthly"}
```

## Further Reading

- [Context Cache](context-cache.md) - Reduce costs with intelligent caching
- [LLM Backends](../llm_backends.md) - Choosing the right model
- [Architecture](architecture.md) - System design overview
