# 🎭 RAE LLM Orchestrator - Provider-Agnostic Intelligence Layer

> **Zero to Many Models** - Run RAE with 0, 1, or N LLMs. Switch providers without changing code.

---

## Overview

The **LLM Orchestrator** decouples RAE from any specific LLM provider. You can:
- ✅ Run **without any LLM** (pure math/heuristics - fastest, zero cost)
- ✅ Use **one model** (OpenAI GPT, Claude, Gemini, etc.)
- ✅ Use **multiple models** with fallback or ensemble strategies
- ✅ Switch providers via configuration (no code changes)
- ✅ Run **fully local** with Ollama (complete data sovereignty)

```
┌────────────────────────────────────────────────────────┐
│                   RAE CORE ENGINE                       │
│   4-Layer Memory + Math Layers + GraphRAG + Reflection │
└─────────────────────┬──────────────────────────────────┘
                      │ LLMRequest (task, strategy)
                      ↓
┌─────────────────────────────────────────────────────────┐
│               LLM ORCHESTRATOR                          │
│   • Strategy Selection (single, fallback, ensemble)    │
│   • Provider Abstraction (OpenAI, Anthropic, Google)   │
│   • Cost Tracking & Budget Management                  │
│   • Telemetry & Monitoring                             │
└──────┬──────────────┬──────────────┬──────────────┬────┘
       │              │              │              │
       ↓              ↓              ↓              ↓
  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐
  │ OpenAI  │   │ Claude  │   │ Gemini  │   │ Ollama  │
  │ GPT-4o  │   │ Sonnet  │   │ Flash   │   │ Llama3  │
  └─────────┘   └─────────┘   └─────────┘   └─────────┘
  Cloud API     Cloud API     Cloud API     Local
```

**Key Principle**: RAE Core never talks directly to LLM providers - only through Orchestrator.

---

## Why LLM Orchestrator?

### The Problem

```
❌ WITHOUT Orchestrator:
- RAE code hardcoded to OpenAI API
- Changing provider = rewrite code
- No fallback on provider failures
- Can't compare model quality
- No local/offline capability
- Cost tracking per provider
```

### The RAE Solution

```
✅ WITH Orchestrator:
- RAE Core provider-agnostic
- Switch models via config file
- Automatic fallback on failures
- A/B test models easily
- Full local mode (Ollama)
- Unified cost tracking
```

---

## Architecture

### Position in RAE System

```
User Query
    ↓
Memory API (FastAPI)
    ↓
Context Builder (needs reflection)
    ↓
LLM Orchestrator (decides: which model? how?)
    ↓
    ├─ Strategy: single → Use primary model
    ├─ Strategy: fallback → Try primary, fallback to secondary
    └─ Strategy: ensemble → Query multiple models, compare
    ↓
LLM Provider (OpenAI, Claude, Gemini, Ollama)
    ↓
LLM Orchestrator (tracks cost, latency, success rate)
    ↓
Return response to RAE Core
```

### Simple Interface

RAE Core sees only one simple interface:

```python
from apps.llm.orchestrator import LLMOrchestrator

orchestrator = LLMOrchestrator()

# Generate text
response = await orchestrator.generate(
    prompt="Generate reflection on authentication failure",
    system_prompt="You are an expert software architect",
    strategy="reflection",  # Uses configured strategy
    tags=["reflection", "failure_analysis"]
)

# Score text
score_response = await orchestrator.score(
    text="JWT token expired",
    criteria="severity",
    strategy="scoring"
)

# Summarize
summary_response = await orchestrator.summarize(
    texts=["Log 1", "Log 2", "Log 3"],
    max_length=200,
    strategy="summaries"
)
```

**Note**: No model names in Core code! Strategy names only.

---

## Configuration

### llm_config.yaml

Complete LLM configuration in one YAML file:

```yaml
# Default strategy when none specified
default_strategy: single

# Model definitions
models:
  # OpenAI GPT-4o
  - id: openai_gpt4o
    provider: openai
    model_name: gpt-4o
    enabled: true
    roles: [general, reflection, coding]
    cost_weight: 1.0
    max_tokens: 4096
    temperature: 0.7

  # OpenAI GPT-3.5-turbo (cheap, fast)
  - id: openai_gpt35
    provider: openai
    model_name: gpt-3.5-turbo
    enabled: true
    roles: [low_cost, summaries]
    cost_weight: 0.1
    max_tokens: 2048

  # Claude Sonnet (quality)
  - id: claude_sonnet
    provider: anthropic
    model_name: claude-3-7-sonnet-20250219
    enabled: false  # Disabled by default
    roles: [analysis, reflection]
    cost_weight: 1.2

  # Google Gemini Flash (fast)
  - id: gemini_flash
    provider: google
    model_name: gemini-1.5-flash
    enabled: true
    roles: [fast, summaries]
    cost_weight: 0.2

  # Local Llama 3 (offline, free)
  - id: local_llama3
    provider: ollama
    model_name: llama3
    enabled: true
    roles: [local, offline, privacy]
    cost_weight: 0.0  # Free!
    base_url: "http://localhost:11434"

# Strategy definitions
strategies:
  # Reflection: Use best model
  reflection:
    mode: single
    primary: openai_gpt4o
    description: "High-quality reflection generation"

  # Summaries: Fast model with fallback
  summaries:
    mode: fallback
    primary: gemini_flash
    fallback: local_llama3
    description: "Fast summaries with local backup"

  # Scoring: Cheap model
  scoring:
    mode: single
    primary: openai_gpt35
    description: "Cost-effective text scoring"

  # Analysis: Multiple models for comparison
  analysis_heavy:
    mode: ensemble
    models: [openai_gpt4o, claude_sonnet]
    description: "Multi-model analysis for critical decisions"

  # Local only: Complete data sovereignty
  local_only:
    mode: single
    primary: local_llama3
    description: "Fully offline operation"
```

**Location**: [`apps/llm/config/llm_config.yaml`](../../apps/llm/config/llm_config.yaml)

---

## Orchestrator Modes

### Mode 1: Single (Simplest)

**How it works**:
1. Use one specified model for the task
2. If model unavailable → return error (or use global fallback)

**Use case**: Simple deployments, single provider

**Example**:
```yaml
strategies:
  reflection:
    mode: single
    primary: openai_gpt4o
```

**Behavior**:
```python
response = await orchestrator.generate(
    prompt="...",
    strategy="reflection"
)
# Uses openai_gpt4o
# If fails → raises LLMUnavailableError
```

---

### Mode 2: Fallback (High Availability)

**How it works**:
1. Try primary model
2. If fails/timeout → automatically try fallback model
3. Response includes which model actually responded

**Use case**: Production systems requiring high availability

**Example**:
```yaml
strategies:
  summaries:
    mode: fallback
    primary: openai_gpt4o
    fallback: local_llama3
```

**Behavior**:
```python
response = await orchestrator.generate(
    prompt="...",
    strategy="summaries"
)
# 1. Try openai_gpt4o
# 2. If fails → try local_llama3
# 3. response.metadata.model_used = "local_llama3" (if fallback used)
```

**Use cases**:
- Cloud model + local backup (for offline capability)
- Primary paid model + fallback free model (cost control)
- High-availability production systems

---

### Mode 3: Ensemble (Multi-Model Quality)

**How it works**:
1. Send same request to 2+ models
2. Collect all responses
3. Choose best response using heuristics:
   - Longest response (more detailed)
   - Highest confidence score
   - Best match to criteria
4. Return best response (+ all responses in metadata)

**Use case**: Critical decisions requiring high confidence

**Example**:
```yaml
strategies:
  analysis_heavy:
    mode: ensemble
    models: [openai_gpt4o, claude_sonnet, gemini_flash]
    selection_method: "longest"  # or "confidence", "voting"
```

**Behavior**:
```python
response = await orchestrator.generate(
    prompt="Analyze this architectural decision",
    strategy="analysis_heavy"
)
# 1. Query openai_gpt4o, claude_sonnet, gemini_flash in parallel
# 2. Collect all 3 responses
# 3. Select best (e.g., longest)
# 4. response.text = "Best response"
# 5. response.metadata.all_responses = [r1, r2, r3]
```

**Future Enhancements**:
- **Competitive mode**: Models compete, reflection layer chooses winner
- **Debate mode**: Models exchange arguments in multiple rounds

---

### Mode 4: No-LLM (Zero Models)

**How it works**:
1. No models configured or all disabled
2. Orchestrator returns:
   - Controlled error (`LLMUnavailableError`), OR
   - Rule-based fallback response

**Use case**:
- Cost constraints (use math/heuristics only)
- Privacy-critical environments (no external APIs)
- Testing without API keys

**Example**:
```yaml
models: []  # No models configured

# OR all models disabled:
models:
  - id: openai_gpt4o
    enabled: false
```

**Behavior**:
```python
response = await orchestrator.generate(
    prompt="...",
    strategy="reflection"
)
# → Raises LLMUnavailableError

# RAE Core handles gracefully:
# - Mark reflection as "manual_review_required"
# - Use heuristic-based fallback
# - Log for later human processing
```

**Benefits**:
- RAE still works (degraded mode)
- Zero API cost
- Complete data sovereignty

---

## Supported Providers

### Cloud Providers

| Provider | Models | API Key Required | Cost | Latency |
|----------|--------|------------------|------|---------|
| **OpenAI** | GPT-4o, GPT-4o-mini, GPT-3.5, O1, O3 | Yes | $$ | 500-2000ms |
| **Anthropic** | Claude 3.5/3.7 Sonnet, Haiku, Opus | Yes | $$$ | 800-3000ms |
| **Google** | Gemini 1.5/2.0 Pro, Flash | Yes | $ | 300-1500ms |
| **DeepSeek** | DeepSeek Coder, Chat | Yes | $ | 1000-3000ms |
| **Qwen** | Qwen 2.5 (Alibaba) | Yes | $ | 1000-2500ms |
| **Grok** | Grok-2 (xAI) | Yes | $$ | 2000-4000ms |

### Local Providers (Ollama)

| Model | Size | RAM Required | Speed | Quality |
|-------|------|--------------|-------|---------|
| **Llama 3** | 8B | 8 GB | Fast | Good |
| **Mistral** | 7B | 8 GB | Fast | Good |
| **Qwen 2.5** | 7B | 8 GB | Fast | Excellent |
| **DeepSeek Coder** | 6.7B | 8 GB | Very Fast | Excellent (code) |
| **Gemma 2** | 9B | 12 GB | Medium | Good |

**Setup**:
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull model
ollama pull llama3

# RAE automatically connects to http://localhost:11434
```

**See**: [Local Setup Guide](../LOCAL_SETUP.md)

---

## Cost Tracking & Budget Management

Orchestrator automatically tracks costs:

```python
# Cost tracking built-in
response = await orchestrator.generate(
    prompt="...",
    strategy="reflection"
)

print(f"Model: {response.metadata.model_used}")
print(f"Tokens: {response.metadata.tokens_used}")
print(f"Cost: ${response.metadata.cost:.4f}")
print(f"Latency: {response.metadata.latency_ms}ms")

# Monthly cost summary
stats = await orchestrator.get_cost_stats(
    start_date=datetime(2025, 12, 1),
    end_date=datetime(2025, 12, 31)
)

print(f"Total cost: ${stats.total_cost:.2f}")
print(f"By provider: {stats.cost_by_provider}")
print(f"By strategy: {stats.cost_by_strategy}")
```

### Budget Enforcement

Orchestrator respects Math-3 policy budget limits:

```python
# When budget exceeded:
try:
    response = await orchestrator.generate(prompt="...")
except BudgetExceededError as e:
    logger.warning(f"Budget exceeded: {e.remaining_budget}")
    # Fallback to:
    # - Cached response
    # - Heuristic-based response
    # - Local free model
```

---

## Real-World Use Cases

### Use Case 1: Cost Optimization

**Problem**: OpenAI GPT-4o costs $0.03/1K tokens. Expensive for high-volume summaries.

**Solution**: Use cheap models for summaries, expensive for critical tasks.

```yaml
strategies:
  summaries:
    mode: single
    primary: gemini_flash  # $0.001/1K tokens (30× cheaper!)

  reflection:
    mode: single
    primary: openai_gpt4o  # Quality matters here
```

**Result**: 70% cost reduction while maintaining reflection quality.

---

### Use Case 2: Offline Operation (Government/Healthcare)

**Problem**: Sensitive data cannot leave premises. No external API calls.

**Solution**: Use local Ollama models only.

```yaml
strategies:
  default:
    mode: single
    primary: local_llama3

models:
  - id: local_llama3
    provider: ollama
    enabled: true
    cost_weight: 0.0  # Free
```

**Result**: Complete data sovereignty. Zero external API calls. Zero cost.

---

### Use Case 3: High Availability

**Problem**: OpenAI API downtime breaks production system.

**Solution**: Fallback to Google Gemini automatically.

```yaml
strategies:
  default:
    mode: fallback
    primary: openai_gpt4o
    fallback: gemini_flash
```

**Result**: 99.9% uptime. Automatic failover.

---

### Use Case 4: A/B Testing Model Quality

**Problem**: Which model generates better reflections? GPT-4o or Claude Sonnet?

**Solution**: Ensemble mode with quality comparison.

```yaml
strategies:
  reflection_test:
    mode: ensemble
    models: [openai_gpt4o, claude_sonnet]
    selection_method: "all"  # Return both for comparison
```

**Result**: Data-driven model selection. Optimize quality vs cost.

---

## Telemetry & Monitoring

Orchestrator tracks comprehensive metrics:

### Metrics Collected

```python
# Per-request metrics
- model_used: str
- strategy_used: str
- latency_ms: float
- tokens_used: int
- cost: float
- success: bool
- error_type: str | None

# Aggregated metrics
- requests_per_model: Dict[str, int]
- cost_per_model: Dict[str, float]
- avg_latency_per_model: Dict[str, float]
- error_rate_per_model: Dict[str, float]
- strategy_usage_distribution: Dict[str, int]
```

### Prometheus Metrics

```python
# Latency
llm_orchestrator_request_duration_seconds{model="openai_gpt4o", strategy="reflection"}

# Cost
llm_orchestrator_request_cost_dollars{model="openai_gpt4o", strategy="reflection"}

# Throughput
llm_orchestrator_requests_total{model="openai_gpt4o", strategy="reflection", status="success"}

# Errors
llm_orchestrator_errors_total{model="openai_gpt4o", error_type="timeout"}

# Budget
llm_orchestrator_monthly_budget_remaining_dollars
```

### Grafana Dashboard

Pre-built dashboard includes:
- **Cost over time** (by model, by strategy)
- **Request latency** (P50, P95, P99)
- **Model usage distribution** (pie chart)
- **Error rates** (by provider)
- **Budget burn rate** (projected vs actual)

**Location**: [`infra/grafana/dashboards/llm-orchestrator.json`](../../infra/grafana/dashboards/)

---

## Configuration Best Practices

### 1. Development vs Production

```yaml
# development.yaml
strategies:
  default:
    mode: single
    primary: local_llama3  # Fast, free, no API keys

# production.yaml
strategies:
  default:
    mode: fallback
    primary: openai_gpt4o
    fallback: gemini_flash  # High availability
```

### 2. Cost Tiers

```yaml
strategies:
  # Tier 1: Critical tasks (quality matters)
  critical:
    mode: ensemble
    models: [openai_gpt4o, claude_sonnet]

  # Tier 2: Standard tasks (balance quality/cost)
  standard:
    mode: single
    primary: openai_gpt4o

  # Tier 3: High-volume tasks (minimize cost)
  high_volume:
    mode: single
    primary: gemini_flash
```

### 3. Privacy-First

```yaml
# For sensitive data: never leave premises
models:
  - id: local_llama3
    provider: ollama
    enabled: true

strategies:
  default:
    mode: single
    primary: local_llama3
```

---

## API Reference

### LLMOrchestrator Methods

```python
class LLMOrchestrator:
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        strategy: str | None = None,
        tags: list[str] | None = None,
        max_tokens: int | None = None,
        temperature: float = 0.7
    ) -> LLMResponse:
        """Generate text using configured strategy."""

    async def score(
        self,
        text: str,
        criteria: str,
        strategy: str | None = None
    ) -> LLMScoreResponse:
        """Score text quality (0.0-1.0)."""

    async def summarize(
        self,
        texts: list[str],
        max_length: int = 200,
        strategy: str | None = None
    ) -> LLMResponse:
        """Summarize multiple texts."""

    async def get_cost_stats(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> CostStats:
        """Get cost statistics for date range."""
```

### Response Models

```python
@dataclass
class LLMResponse:
    text: str                       # Generated text
    metadata: LLMMetadata           # Model info, cost, latency
    strategy_used: str              # Which strategy was used
    success: bool                   # True if successful

@dataclass
class LLMMetadata:
    model_used: str                 # Actual model that responded
    tokens_used: int                # Total tokens (prompt + completion)
    cost: float                     # Cost in USD
    latency_ms: float               # Request latency
    all_responses: list[str] | None # For ensemble mode
```

---

## 📚 Related Documentation

- **[Memory Layers](./MEMORY_LAYERS.md)** - 4-layer cognitive architecture
- **[Math Layers](./MATH_LAYERS.md)** - Decision intelligence & cost optimization
- **[Cost Controller](../reference/concepts/cost-controller.md)** - Budget management
- **[Local Setup Guide](../LOCAL_SETUP.md)** - Offline Ollama configuration
- **[LLM Backends](../reference/llm/llm_backends.md)** - Provider-specific setup

---

## 🔬 Implementation Status

| Feature | Status | Tests | Coverage |
|---------|--------|-------|----------|
| **Single Mode** | ✅ Complete | 35 tests | 92% |
| **Fallback Mode** | ✅ Complete | 28 tests | 88% |
| **Ensemble Mode** | 🟡 Beta | 15 tests | 75% |
| **No-LLM Mode** | ✅ Complete | 20 tests | 90% |
| **Cost Tracking** | ✅ Complete | 42 tests | 95% |
| **Telemetry** | ✅ Complete | 18 tests | 85% |
| **Config Hot-Reload** | ⏳ Planned | 0 tests | 0% |

**Code Location**: [`apps/llm/orchestrator.py`](../../apps/llm/orchestrator.py)

---

**Version**: 2.1.1
**Last Updated**: 2025-12-08
**Status**: Production Ready (Single, Fallback, No-LLM) / Beta (Ensemble) ✅

**See also**: [Main README](../../README.md) | [Architecture Overview](../reference/concepts/architecture.md)
