# Orchestrator Refactoring - Provider-Agnostic Architecture

**Date**: 2025-12-10
**Goal**: Make orchestrator independent of LLM providers
**Status**: 🔄 IN PROGRESS

---

## Problem

Current architecture is hardcoded for Claude and Gemini:
- `ModelType` enum has specific models (CLAUDE_SONNET, GEMINI_PRO, GEMINI_FLASH)
- Adapters are tightly coupled to specific APIs
- Adding new provider (Ollama, OpenAI, etc.) requires code changes
- No plugin system for extending providers

## Solution

Create provider-agnostic architecture with:
1. **Abstract Provider Interface** - Common contract for all LLM providers
2. **Provider Registry** - Dynamic registration and discovery
3. **Model Capabilities** - Metadata about what each model can do
4. **Unified Configuration** - Provider-specific settings
5. **Backward Compatibility** - Existing code still works

---

## Architecture Design

### 1. Provider Interface

```python
class LLMProvider(ABC):
    """Abstract interface for LLM providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name (e.g., 'claude', 'gemini', 'ollama')."""
        pass

    @property
    @abstractmethod
    def available_models(self) -> List[ModelInfo]:
        """List of available models from this provider."""
        pass

    @abstractmethod
    async def generate(
        self,
        model: str,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> GenerationResult:
        """Generate completion from model."""
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if provider is configured and available."""
        pass

    @abstractmethod
    def get_model_info(self, model: str) -> ModelInfo:
        """Get information about specific model."""
        pass
```

### 2. Model Metadata

```python
@dataclass
class ModelInfo:
    """Metadata about a model."""
    provider: str              # Provider name
    model_id: str             # Model identifier
    display_name: str         # Human-readable name
    capabilities: List[str]   # ['code', 'analysis', 'planning', etc.]
    context_window: int       # Max context tokens
    cost_per_1k_input: float  # USD per 1K input tokens
    cost_per_1k_output: float # USD per 1K output tokens
    tier: ModelTier           # FAST, STANDARD, ADVANCED

    def supports(self, capability: str) -> bool:
        """Check if model supports capability."""
        return capability in self.capabilities
```

### 3. Provider Registry

```python
class ProviderRegistry:
    """Central registry for LLM providers."""

    def __init__(self):
        self._providers: Dict[str, LLMProvider] = {}
        self._models: Dict[str, ModelInfo] = {}

    def register(self, provider: LLMProvider):
        """Register a provider."""
        self._providers[provider.name] = provider
        for model_info in provider.available_models:
            self._models[model_info.model_id] = model_info

    def get_provider(self, name: str) -> Optional[LLMProvider]:
        """Get provider by name."""
        return self._providers.get(name)

    def get_model_info(self, model_id: str) -> Optional[ModelInfo]:
        """Get model metadata."""
        return self._models.get(model_id)

    def list_models(
        self,
        capability: Optional[str] = None,
        max_cost: Optional[float] = None,
        tier: Optional[ModelTier] = None
    ) -> List[ModelInfo]:
        """List models matching criteria."""
        models = list(self._models.values())

        if capability:
            models = [m for m in models if m.supports(capability)]
        if max_cost:
            models = [m for m in models if m.cost_per_1k_input <= max_cost]
        if tier:
            models = [m for m in models if m.tier == tier]

        return models
```

### 4. Smart Routing (Updated)

```python
class ModelRouter:
    """Routes tasks to appropriate models (provider-agnostic)."""

    def __init__(self, registry: ProviderRegistry):
        self.registry = registry

    def choose_model(
        self,
        role: str,
        risk: TaskRisk,
        area: str,
        complexity: TaskComplexity
    ) -> RoutingDecision:
        """Choose best model for task based on criteria."""

        # Define requirements
        if risk == TaskRisk.HIGH:
            tier = ModelTier.ADVANCED
            capability = "complex_reasoning"
        elif risk == TaskRisk.MEDIUM:
            tier = ModelTier.STANDARD
            capability = "code"
        else:
            tier = ModelTier.FAST
            capability = "code"

        # Find matching models
        candidates = self.registry.list_models(
            capability=capability,
            tier=tier
        )

        if not candidates:
            # Fallback to any model
            candidates = self.registry.list_models()

        # Choose cheapest matching model
        model = min(candidates, key=lambda m: m.cost_per_1k_input)

        return RoutingDecision(
            model_id=model.model_id,
            provider=model.provider,
            rationale=f"{tier.value} tier, {capability} capability",
            estimated_cost=model.cost_per_1k_input * 3  # Estimate
        )
```

---

## Implementation Plan

### Phase 1: Core Abstractions

**Files to create**:
- `orchestrator/providers/__init__.py`
- `orchestrator/providers/base.py` - Abstract interfaces
- `orchestrator/providers/registry.py` - Provider registry
- `orchestrator/providers/models.py` - Model metadata

**Changes**:
```python
# Before
from orchestrator.adapters import ModelType, ClaudeAdapter

adapter = ClaudeAdapter(ModelType.CLAUDE_SONNET, working_dir)

# After
from orchestrator.providers import ProviderRegistry

registry = ProviderRegistry()
model_info = registry.get_model_info("claude-sonnet-4-5")
provider = registry.get_provider(model_info.provider)
result = await provider.generate(
    model=model_info.model_id,
    prompt=prompt
)
```

### Phase 2: Migrate Existing Adapters

**Refactor**:
- `orchestrator/adapters/claude_adapter.py` → `orchestrator/providers/claude.py`
- `orchestrator/adapters/gemini_adapter.py` → `orchestrator/providers/gemini.py`

**Implement**:
```python
class ClaudeProvider(LLMProvider):
    """Claude provider implementation."""

    @property
    def name(self) -> str:
        return "claude"

    @property
    def available_models(self) -> List[ModelInfo]:
        return [
            ModelInfo(
                provider="claude",
                model_id="claude-sonnet-4-5",
                display_name="Claude Sonnet 4.5",
                capabilities=["code", "analysis", "planning", "complex_reasoning"],
                context_window=200000,
                cost_per_1k_input=0.003,
                cost_per_1k_output=0.015,
                tier=ModelTier.ADVANCED
            ),
            # ... more models
        ]

    async def generate(self, model: str, prompt: str, **kwargs) -> GenerationResult:
        """Use Anthropic API."""
        response = await self.client.messages.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            **kwargs
        )
        return GenerationResult(
            content=response.content[0].text,
            usage=Usage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens
            )
        )
```

### Phase 3: Add New Providers

**Ollama Provider**:
```python
class OllamaProvider(LLMProvider):
    """Local Ollama provider."""

    @property
    def available_models(self) -> List[ModelInfo]:
        return [
            ModelInfo(
                provider="ollama",
                model_id="llama3:70b",
                display_name="Llama 3 70B",
                capabilities=["code", "analysis"],
                context_window=8192,
                cost_per_1k_input=0.0,  # Local, free
                cost_per_1k_output=0.0,
                tier=ModelTier.STANDARD
            ),
            # ... more models
        ]
```

**OpenAI Provider**:
```python
class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider."""

    @property
    def available_models(self) -> List[ModelInfo]:
        return [
            ModelInfo(
                provider="openai",
                model_id="gpt-4-turbo",
                display_name="GPT-4 Turbo",
                capabilities=["code", "analysis", "planning"],
                context_window=128000,
                cost_per_1k_input=0.01,
                cost_per_1k_output=0.03,
                tier=ModelTier.ADVANCED
            ),
            # ... more models
        ]
```

### Phase 4: Configuration System

**Provider Configuration** (`.orchestrator/providers.yaml`):
```yaml
providers:
  claude:
    enabled: true
    api_key: ${ANTHROPIC_API_KEY}
    default_model: claude-sonnet-4-5

  gemini:
    enabled: true
    auth_method: cli  # Uses gemini CLI
    default_model: gemini-2.0-flash

  ollama:
    enabled: true
    endpoint: http://localhost:11434
    default_model: llama3:70b

  openai:
    enabled: false  # Not configured yet
    api_key: ${OPENAI_API_KEY}
    default_model: gpt-4-turbo

routing:
  prefer_local: true  # Use local models (Ollama) when possible
  max_cost_per_task: 1.0  # USD
  fallback_provider: claude  # If preferred unavailable
```

### Phase 5: Update Orchestrator

**Before**:
```python
# Hardcoded model selection
if risk == TaskRisk.HIGH:
    adapter = ClaudeAdapter(ModelType.CLAUDE_SONNET, working_dir)
else:
    adapter = GeminiAdapter(ModelType.GEMINI_FLASH, working_dir)
```

**After**:
```python
# Dynamic routing
routing_decision = router.choose_model(
    role="planner",
    risk=task_risk,
    area=task_area,
    complexity=task_complexity
)

provider = registry.get_provider(routing_decision.provider)
result = await provider.generate(
    model=routing_decision.model_id,
    prompt=prompt
)
```

---

## Migration Strategy

### Step 1: Create New Architecture (Non-Breaking)

Create `orchestrator/providers/` alongside existing `orchestrator/adapters/`:
- Both can coexist
- Orchestrator uses old adapters initially
- New code uses providers

### Step 2: Migrate Internally

Update orchestrator to use provider registry:
- Keep same external API
- Internal implementation uses providers
- Tests verify backward compatibility

### Step 3: Deprecate Old Adapters

Mark `orchestrator/adapters/` as deprecated:
- Add deprecation warnings
- Update documentation
- Provide migration guide

### Step 4: Remove Old Code (v2.0)

Eventually remove old adapters:
- Clean up codebase
- Full provider-agnostic architecture

---

## Benefits

### 1. Flexibility
- Add new providers without code changes
- Swap providers based on cost, performance, availability
- Test with local models (Ollama) before production

### 2. Cost Optimization
- Use cheapest model that meets requirements
- Fallback to free local models when possible
- Set cost limits per task

### 3. Resilience
- Failover to alternative providers
- Continue working if one provider is down
- Rate limit handling across providers

### 4. Testability
- Mock providers for testing
- Use local models in CI/CD
- Consistent interface for all providers

---

## Example Usage

### Register Providers

```python
from orchestrator.providers import (
    ProviderRegistry,
    ClaudeProvider,
    GeminiProvider,
    OllamaProvider
)

# Initialize registry
registry = ProviderRegistry()

# Register providers
registry.register(ClaudeProvider())
registry.register(GeminiProvider())
registry.register(OllamaProvider(endpoint="http://localhost:11434"))

# Use in orchestrator
orchestrator = Orchestrator(
    working_dir=".",
    provider_registry=registry
)
```

### Dynamic Routing

```python
# Find best model for high-risk planning
models = registry.list_models(
    capability="complex_reasoning",
    tier=ModelTier.ADVANCED
)

# Sort by cost
models.sort(key=lambda m: m.cost_per_1k_input)

# Use cheapest advanced model
best_model = models[0]
print(f"Using {best_model.display_name} at ${best_model.cost_per_1k_input:.4f}/1K")
```

### Provider Fallback

```python
# Try preferred provider, fallback to others
preferred = ["ollama", "gemini", "claude"]

for provider_name in preferred:
    provider = registry.get_provider(provider_name)
    if provider and await provider.is_available():
        result = await provider.generate(...)
        break
else:
    raise RuntimeError("No providers available")
```

---

## File Structure (After Refactor)

```
orchestrator/
├── providers/                  # NEW - Provider-agnostic
│   ├── __init__.py
│   ├── base.py                # Abstract interfaces
│   ├── registry.py            # Provider registry
│   ├── models.py              # Model metadata
│   ├── claude.py              # Claude provider
│   ├── gemini.py              # Gemini provider
│   ├── ollama.py              # Ollama provider (local)
│   └── openai.py              # OpenAI provider
├── adapters/                   # DEPRECATED - Old code
│   └── (kept for backward compat)
├── core/
│   ├── model_router.py        # UPDATED - Uses registry
│   └── ...
└── main.py                    # UPDATED - Uses providers

.orchestrator/
├── tasks.yaml
└── providers.yaml             # NEW - Provider config
```

---

## Testing Strategy

### Unit Tests

```python
# Test provider interface
async def test_provider_generate():
    provider = ClaudeProvider(api_key="test")
    result = await provider.generate(
        model="claude-sonnet-4-5",
        prompt="test"
    )
    assert result.content

# Test registry
def test_registry_list_models():
    registry = ProviderRegistry()
    registry.register(ClaudeProvider())

    models = registry.list_models(capability="code")
    assert len(models) > 0
```

### Integration Tests

```python
# Test with mock provider
class MockProvider(LLMProvider):
    async def generate(self, model, prompt, **kwargs):
        return GenerationResult(content="mock response")

# Use in orchestrator
registry = ProviderRegistry()
registry.register(MockProvider())

orchestrator = Orchestrator(registry=registry)
result = await orchestrator.run_task(task_def)
```

---

## Timeline

- **Day 1**: Core abstractions (base, registry, models)
- **Day 2**: Migrate Claude + Gemini to new interface
- **Day 3**: Add Ollama + OpenAI providers
- **Day 4**: Update orchestrator + router
- **Day 5**: Testing + documentation

**Total**: ~5 days for complete refactoring

---

## Success Criteria

✅ **New provider can be added in <50 lines of code**
✅ **Orchestrator works with any registered provider**
✅ **Cost-based routing works across providers**
✅ **Backward compatibility maintained**
✅ **Documentation complete**
✅ **All tests passing**

---

## Status

✅ **PHASE 1-3 COMPLETE** - Core abstractions and providers implemented
⏳ **PHASE 4-5 PENDING** - Orchestrator migration and adapter deprecation

### Completed (Phase 2.5):

✅ **Phase 1: Core Abstractions**
- Created `orchestrator/providers/base.py` with abstract interfaces
- Implemented `LLMProvider`, `ModelInfo`, `ModelTier`, `GenerationResult`, `Usage`
- Implemented `ProviderRegistry` for dynamic registration

✅ **Phase 2: Migrate Existing Adapters**
- Created `orchestrator/providers/claude.py` - ClaudeProvider implementation
- Created `orchestrator/providers/gemini.py` - GeminiProvider implementation
- Backward compatibility maintained via adapter wrappers

✅ **Phase 3: Add New Providers**
- Created `orchestrator/providers/ollama.py` - Local model support example
- Demonstrated <50 lines to add new provider

✅ **Phase 4: Configuration System (Partial)**
- Created `orchestrator/providers/config.py` - YAML configuration loader
- Created `.orchestrator/providers.yaml` - Default provider configuration
- Environment variable expansion support (${ANTHROPIC_API_KEY})

✅ **Phase 5: Update Router (New Implementation)**
- Created `orchestrator/core/model_router_v2.py` - Provider-agnostic router
- Maintains same intelligent routing rules
- Supports dynamic model discovery by capability/tier/cost

✅ **Documentation**
- Updated `orchestrator/README.md` with Phase 2.5 section
- Added provider system usage examples
- Documented how to add new providers

### Remaining Work:

⏳ **Orchestrator Migration**
- Update `orchestrator/main.py` to use ProviderRegistry
- Update agents to use new provider system
- Migration script for existing deployments

⏳ **Testing & Validation**
- Unit tests for all providers
- Integration tests with mock providers
- Cost optimization validation
- Performance benchmarks

⏳ **Deprecation Path**
- Mark `orchestrator/adapters/` as deprecated
- Add migration guide
- Gradual removal timeline (v2.0)

### Next Steps:

1. Create integration tests for provider system
2. Update main orchestrator to use ModelRouterV2
3. Add migration documentation
4. Test with real workloads
5. Deprecate old adapters in next major version
