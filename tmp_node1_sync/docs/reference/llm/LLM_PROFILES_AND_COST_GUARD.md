# LLM Profiles and Cost Guard

## Overview

RAE supports multiple LLM providers with sophisticated cost tracking, budgets, and automatic fallback chains. The Cost Guard prevents budget overruns with real-time monitoring and HTTP 402 blocking.

## Supported LLM Providers

| Provider | Models | API Key Env Var |
|----------|--------|-----------------|
| **OpenAI** | gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo | `OPENAI_API_KEY` |
| **Anthropic** | claude-3-5-sonnet, claude-3-opus, claude-3-haiku | `ANTHROPIC_API_KEY` |
| **Google** | gemini-pro, gemini-1.5-pro | `GOOGLE_API_KEY` |
| **DeepSeek** | deepseek-chat, deepseek-coder | `DEEPSEEK_API_KEY` |
| **Qwen** | qwen-turbo, qwen-plus, qwen-max | `QWEN_API_KEY` |
| **Grok** | grok-beta | `XAI_API_KEY` |
| **Ollama** | llama3, mistral, codellama (local) | `OLLAMA_BASE_URL` |

## LLM Profiles

### Profile Structure

```python
{
  "profile_id": "default",
  "tenant_id": "tenant-123",
  "model": "gpt-4o",
  "provider": "openai",
  "fallback_chain": ["gpt-4o", "gpt-4o-mini", "ollama/llama3"],
  "cost_per_1k_input_tokens": 0.005,
  "cost_per_1k_output_tokens": 0.015,
  "max_tokens": 4096,
  "temperature": 0.7,
  "enable_caching": true
}
```

### Configuration

#### Environment Variables

```bash
# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_ORG_ID=org-...

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Google
GOOGLE_API_KEY=...
GOOGLE_PROJECT_ID=...

# DeepSeek
DEEPSEEK_API_KEY=...

# Ollama (Local)
OLLAMA_BASE_URL=http://localhost:11434

# Default Model
RAE_LLM_MODEL_DEFAULT=gpt-4o
```

#### Profile Configuration File

Example `llm_profiles.yaml`:

```yaml
profiles:
  - id: high-quality
    model: gpt-4o
    provider: openai
    temperature: 0.3
    max_tokens: 8192
    fallback_chain:
      - gpt-4o
      - claude-3-5-sonnet
      - gpt-4o-mini

  - id: cost-optimized
    model: gpt-4o-mini
    provider: openai
    temperature: 0.7
    max_tokens: 4096
    fallback_chain:
      - gpt-4o-mini
      - ollama/llama3

  - id: local-only
    model: llama3
    provider: ollama
    temperature: 0.7
    max_tokens: 4096
```

### Fallback Chains

Automatic failover on errors or rate limits:

```python
# Example fallback chain: expensive → mid → cheap → local
fallback_chain = [
    "gpt-4o",           # Try premium model first
    "gpt-4o-mini",      # Fall back to cheaper model
    "ollama/llama3"     # Ultimate fallback to local
]

# On failure, automatically tries next in chain
```

## Cost Guard

### Features

- **Real-time cost tracking**: Track costs per request, tenant, profile
- **Budget enforcement**: Block requests when budget exceeded (HTTP 402)
- **Alerts**: Email/webhook notifications at threshold %
- **Audit trail**: Full cost logs for compliance

### Budget Configuration

#### Per-Tenant Budget

```python
{
  "tenant_id": "tenant-123",
  "monthly_budget_usd": 500,
  "alert_thresholds": [0.8, 0.9, 0.95],  # Alert at 80%, 90%, 95%
  "action_on_exceed": "block"  # or "alert_only"
}
```

#### Per-Profile Budget

```python
{
  "profile_id": "high-quality",
  "tenant_id": "tenant-123",
  "monthly_budget_usd": 200
}
```

### Cost Calculation

Costs are calculated per request:

```python
# For each LLM call:
input_cost = (input_tokens / 1000) * profile.cost_per_1k_input_tokens
output_cost = (output_tokens / 1000) * profile.cost_per_1k_output_tokens
total_cost = input_cost + output_cost

# Store in cost_logs table
await cost_service.log_cost(
    tenant_id=tenant_id,
    profile_id=profile_id,
    model=model,
    input_tokens=input_tokens,
    output_tokens=output_tokens,
    cost_usd=total_cost
)
```

### Budget Enforcement

When budget exceeded:

```http
POST /api/v1/memories
X-Tenant-ID: tenant-123
...

HTTP/1.1 402 Payment Required
Content-Type: application/json

{
  "error": "Budget exceeded",
  "message": "Monthly budget of $500 has been exceeded. Current usage: $523.45",
  "budget_usd": 500.00,
  "current_usage_usd": 523.45,
  "budget_remaining_usd": -23.45
}
```

### Cost Monitoring

#### Query Current Usage

```python
from apps.memory_api.services.cost_controller import CostController

cost_service = CostController(pool)

usage = await cost_service.get_monthly_usage(tenant_id="tenant-123")

# Returns:
# {
#   "tenant_id": "tenant-123",
#   "month": "2025-12",
#   "total_cost_usd": 347.23,
#   "budget_usd": 500.00,
#   "budget_remaining_usd": 152.77,
#   "budget_percent_used": 0.6945,
#   "breakdown_by_profile": {
#     "default": 200.50,
#     "high-quality": 146.73
#   }
# }
```

#### Cost Logs Table

```sql
CREATE TABLE cost_logs (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    profile_id VARCHAR(255),
    model VARCHAR(255) NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    cost_usd DECIMAL(10, 6) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB
);

-- Index for fast queries
CREATE INDEX idx_cost_logs_tenant_timestamp
  ON cost_logs(tenant_id, timestamp DESC);
```

## Provider Matrix

### Model Pricing (as of 2025)

| Provider | Model | Input ($/1K tokens) | Output ($/1K tokens) |
|----------|-------|---------------------|----------------------|
| OpenAI | gpt-4o | $0.005 | $0.015 |
| OpenAI | gpt-4o-mini | $0.00015 | $0.0006 |
| Anthropic | claude-3-5-sonnet | $0.003 | $0.015 |
| Anthropic | claude-3-haiku | $0.00025 | $0.00125 |
| Google | gemini-1.5-pro | $0.0035 | $0.0105 |
| DeepSeek | deepseek-chat | $0.00014 | $0.00028 |
| Ollama | llama3 (local) | $0.00 | $0.00 |

### Provider-Specific Configuration

#### OpenAI

```bash
OPENAI_API_KEY=sk-...
OPENAI_ORG_ID=org-...
OPENAI_BASE_URL=https://api.openai.com/v1  # Optional
```

#### Anthropic

```bash
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_BASE_URL=https://api.anthropic.com  # Optional
```

#### Ollama (Local)

```bash
OLLAMA_BASE_URL=http://localhost:11434

# Pull models
ollama pull llama3
ollama pull mistral
```

## Usage Examples

### Using Specific Profile

```python
from apps.memory_api.services.llm import get_llm_provider

llm = get_llm_provider(profile_id="high-quality")

response = await llm.generate(
    system="You are a helpful assistant",
    prompt="Explain quantum computing",
    max_tokens=500
)

# Costs automatically tracked and logged
```

### Structured Output

```python
from pydantic import BaseModel

class Summary(BaseModel):
    summary: str
    key_points: List[str]
    sentiment: str

llm = get_llm_provider()

response = await llm.generate_structured(
    system="Summarize the text",
    prompt="Text to summarize...",
    response_model=Summary
)

# Returns: Summary(summary="...", key_points=[...], sentiment="positive")
```

### Streaming

```python
llm = get_llm_provider()

async for chunk in llm.generate_stream(
    system="You are a helpful assistant",
    prompt="Write a story about AI"
):
    print(chunk, end="", flush=True)
```

## Monitoring and Alerting

### Prometheus Metrics

```
# Total cost across all tenants
rae_llm_cost_usd_total{tenant_id="tenant-123", profile_id="default"}

# Token usage
rae_llm_tokens_total{tenant_id="tenant-123", type="input"}
rae_llm_tokens_total{tenant_id="tenant-123", type="output"}

# Request counts
rae_llm_requests_total{tenant_id="tenant-123", model="gpt-4o", status="success"}

# Budget status
rae_llm_budget_percent{tenant_id="tenant-123"}
```

### Alert Rules

Example Prometheus alert:

```yaml
- alert: LLMBudgetExceeded
  expr: rae_llm_budget_percent > 0.95
  annotations:
    summary: "LLM budget exceeded 95% for tenant {{ $labels.tenant_id }}"
```

## Cost Optimization Strategies

### 1. Use Appropriate Models

- **Simple tasks**: gpt-4o-mini, claude-3-haiku
- **Complex reasoning**: gpt-4o, claude-3-5-sonnet
- **Development/testing**: ollama/llama3 (local)

### 2. Enable Caching

```python
{
  "enable_caching": true,  # Cache LLM responses
  "cache_ttl_seconds": 3600
}
```

### 3. Token Limits

```python
{
  "max_tokens": 500,  # Limit output length
  "max_input_tokens": 4000  # Truncate long inputs
}
```

### 4. Batch Processing

Process multiple items in single LLM call:

```python
# Instead of 10 separate calls:
for item in items:
    await llm.generate(f"Summarize: {item}")

# Batch into single call:
batch_prompt = "\n".join([f"{i}. {item}" for i, item in enumerate(items)])
response = await llm.generate(f"Summarize each item:\n{batch_prompt}")
```

## Related Documentation

- [Multi-Tenancy](./MULTI_TENANCY.md) - Per-tenant budgets
- [Background Workers](./BACKGROUND_WORKERS.md) - LLM usage in workers
- [Reflection Engine](./REFLECTION_ENGINE_V2_IMPLEMENTATION.md) - LLM for reflections
