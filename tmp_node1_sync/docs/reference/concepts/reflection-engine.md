# Reflection Engine

The **Reflection Engine** is RAE's intelligent insight extraction system that automatically analyzes episodic memories to generate higher-level semantic knowledge and long-term insights.

## Overview

Think of the Reflection Engine as RAE's "subconscious" - it continuously processes experiences (episodic memories) in the background to extract patterns, insights, and wisdom.

```
┌─────────────────────────────────────────────────────┐
│  EPISODIC MEMORIES                                  │
│  - User fixed auth bug on Monday                    │
│  - User fixed another auth bug on Wednesday         │
│  - User mentioned auth.py is problematic            │
│  - User refactored auth.py on Friday                │
└──────────────────┬──────────────────────────────────┘
                   │
                   │ Reflection Engine
                   │ (LLM-powered analysis)
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│  SEMANTIC MEMORY                                    │
│  "The authentication module has recurring issues    │
│   and requires frequent bug fixes"                  │
└──────────────────┬──────────────────────────────────┘
                   │
                   │ Further reflection
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│  LONG-TERM MEMORY                                   │
│  "Authentication module should be refactored to     │
│   improve reliability and reduce maintenance"       │
└─────────────────────────────────────────────────────┘
```

## How It Works

### 1. Collection Phase

The Reflection Engine periodically collects recent episodic memories:

```python
# Collect memories from last 7 days
recent_memories = await get_memories(
    layer="episodic",
    since=datetime.now() - timedelta(days=7),
    limit=50
)
```

### 2. Analysis Phase

An LLM analyzes the collected memories to identify:
- **Patterns**: Recurring events or behaviors
- **Relationships**: Connections between different memories
- **Insights**: Higher-level understanding
- **Anomalies**: Unusual or important events

**Example Prompt:**
```python
prompt = f"""
Analyze the following memories and extract key insights:

{memories}

Identify:
1. Common patterns or repeated behaviors
2. Important facts or preferences
3. Relationships between events
4. Actionable insights

Format as structured JSON with:
- insight: The extracted insight
- confidence: 0-1 confidence score
- evidence: IDs of supporting memories
- category: Type of insight (pattern, preference, fact, etc.)
"""
```

### 3. Generation Phase

The LLM generates semantic memories or long-term insights:

```json
{
  "insight": "User consistently prefers TypeScript over JavaScript for new projects",
  "confidence": 0.95,
  "evidence": ["mem_123", "mem_456", "mem_789"],
  "category": "preference",
  "importance": 0.8
}
```

### 4. Storage Phase

Generated insights are stored in appropriate layers:

```python
# Store as semantic memory
await store_memory(
    content=insight["insight"],
    layer="semantic",
    metadata={
        "confidence": insight["confidence"],
        "derived_from": insight["evidence"],
        "category": insight["category"],
        "generated_by": "reflection_engine",
        "generated_at": datetime.now()
    }
)
```

## Reflection Triggers

### Scheduled Reflection

Runs automatically on a schedule:

```python
# celery_app.py
from celery.schedules import crontab

@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Run reflection every 6 hours
    sender.add_periodic_task(
        crontab(hour='*/6'),
        reflect_on_memories.s(),
        name='periodic_reflection'
    )
```

### Manual Reflection

Trigger reflection on demand:

```python
# Via API
result = await client.generate_reflection(
    memory_limit=100,
    min_age_hours=1,
    max_age_days=7
)
```

```bash
# Via CLI
curl -X POST http://localhost:8000/v1/agent/reflect \
  -H "X-Tenant-ID: demo-tenant" \
  -H "Content-Type: application/json" \
  -d '{
    "memory_limit": 50,
    "focus": "code_quality"
  }'
```

### Event-Driven Reflection

Triggered by specific events:

```python
# After significant event
@app.post("/v1/memory/store")
async def store_memory(memory: MemoryCreate):
    stored = await memory_service.store(memory)

    # Trigger reflection if important
    if memory.importance > 0.8:
        await trigger_reflection.delay(
            focus_memory_id=stored.id
        )

    return stored
```

## Reflection Strategies

### 1. Pattern Detection

Identifies recurring patterns across memories:

```python
def detect_patterns(memories: List[Memory]) -> List[Pattern]:
    """
    Detect patterns in episodic memories.

    Examples:
    - User always codes in the morning
    - User frequently asks about authentication
    - User prefers certain libraries
    """
    # Group by similarity
    clusters = cluster_by_content(memories)

    patterns = []
    for cluster in clusters:
        if len(cluster) >= 3:  # Pattern needs 3+ occurrences
            pattern = extract_pattern(cluster)
            patterns.append(pattern)

    return patterns
```

### 2. Consolidation

Merges similar episodic memories into concise semantic knowledge:

```python
# Multiple episodes
episodes = [
    "User fixed bug in auth.py line 42",
    "User fixed another bug in auth.py line 89",
    "User refactored auth.py to fix recurring issues"
]

# Consolidated semantic memory
semantic = "The authentication module (auth.py) has had multiple bugs that required fixes and eventual refactoring"
```

### 3. Abstraction

Extracts abstract principles from specific events:

```python
# Specific events
events = [
    "User chose TypeScript for project A",
    "User chose TypeScript for project B",
    "User converted project C from JavaScript to TypeScript"
]

# Abstract principle
principle = "User prefers TypeScript over JavaScript for all projects"
```

### 4. Causal Reasoning

Identifies cause-effect relationships:

```python
# Related memories
memories = [
    "User experienced slow query performance",
    "User added database index on user_id column",
    "User reported query performance improved significantly"
]

# Causal insight
insight = "Adding database indexes improves query performance, particularly for frequently queried columns like user_id"
```

## Reflection Quality

### Confidence Scoring

Each reflection has a confidence score (0-1):

```python
def calculate_confidence(insight: Insight) -> float:
    """
    Calculate confidence based on:
    - Number of supporting memories (more = higher)
    - Consistency of evidence (less variation = higher)
    - Recency of memories (recent = higher)
    - LLM's confidence score
    """

    evidence_score = min(len(insight.evidence) / 5, 1.0)  # More evidence = better
    recency_score = calculate_recency(insight.evidence)
    consistency_score = calculate_consistency(insight.evidence)
    llm_score = insight.llm_confidence

    return (
        0.3 * evidence_score +
        0.2 * recency_score +
        0.3 * consistency_score +
        0.2 * llm_score
    )
```

### Verification

Reflections can be verified against new evidence:

```python
@celery.task
def verify_reflection(reflection_id: str):
    """
    Verify existing reflection against new memories.

    Updates confidence score or archives if no longer valid.
    """
    reflection = await get_reflection(reflection_id)
    new_evidence = await find_related_memories(reflection)

    if supports_reflection(new_evidence, reflection):
        # Increase confidence
        reflection.confidence = min(reflection.confidence + 0.1, 1.0)
    elif contradicts_reflection(new_evidence, reflection):
        # Decrease confidence or archive
        reflection.confidence = max(reflection.confidence - 0.2, 0.0)
        if reflection.confidence < 0.3:
            reflection.status = "archived"

    await update_reflection(reflection)
```

## Configuration

### Reflection Settings

```env
# .env
# Enable/disable reflection engine
ENABLE_REFLECTION=true

# How often to run reflection (cron format)
REFLECTION_SCHEDULE="0 */6 * * *"  # Every 6 hours

# Minimum memories needed to trigger reflection
REFLECTION_MIN_MEMORIES=10

# Maximum memories to analyze per reflection
REFLECTION_MAX_MEMORIES=100

# Minimum confidence for storing reflections
REFLECTION_MIN_CONFIDENCE=0.7

# LLM model for reflection
REFLECTION_LLM_MODEL=gpt-4  # or claude-3-opus, gemini-pro
```

### Per-Tenant Configuration

```python
# Different settings per tenant
tenant_config = {
    "reflection_enabled": True,
    "reflection_frequency_hours": 6,
    "min_confidence": 0.8,
    "focus_areas": ["code_quality", "user_preferences"]
}
```

## API Usage

### Generate Reflection

```python
from rae_memory_sdk import MemoryClient

client = MemoryClient(api_url="http://localhost:8000")

# Generate reflection from recent memories
reflection = await client.generate_reflection(
    memory_limit=50,
    min_confidence=0.7,
    focus="coding_patterns"
)

print(f"Insight: {reflection['content']}")
print(f"Confidence: {reflection['confidence']}")
print(f"Based on {len(reflection['evidence'])} memories")
```

### List Reflections

```python
# Get all reflections
reflections = await client.list_reflections(
    layer="semantic",
    min_confidence=0.8
)

for ref in reflections:
    print(f"{ref['category']}: {ref['content']}")
```

### Query by Reflection

```python
# Find memories that led to a specific insight
reflection_id = "refl_123"
source_memories = await client.get_reflection_sources(reflection_id)

for memory in source_memories:
    print(f"- {memory['content']}")
```

## Advanced Features

### Multi-Agent Reflection

Different agents can reflect on shared memories:

```python
# Agent A's perspective
agent_a_reflection = await reflect(
    memories=shared_memories,
    perspective="code_reviewer",
    focus="code_quality"
)

# Agent B's perspective
agent_b_reflection = await reflect(
    memories=shared_memories,
    perspective="architect",
    focus="system_design"
)
```

### Hierarchical Reflection

Reflections can be reflected upon:

```
Episodic → Semantic (daily reflection)
           ↓
       Semantic → LTM (weekly reflection)
                   ↓
               LTM → Wisdom (monthly reflection)
```

```python
# Weekly meta-reflection on semantic memories
weekly_insights = await reflect_on_reflections(
    layer="semantic",
    since=datetime.now() - timedelta(days=7),
    target_layer="ltm"
)
```

### Collaborative Reflection

Multiple LLMs can provide different perspectives:

```python
# Use multiple models for reflection
gpt4_insight = await reflect(memories, model="gpt-4")
claude_insight = await reflect(memories, model="claude-3-opus")
gemini_insight = await reflect(memories, model="gemini-pro")

# Synthesize insights
combined_insight = await synthesize_insights([
    gpt4_insight,
    claude_insight,
    gemini_insight
])
```

## Best Practices

### 1. Regular Reflection

Run reflection regularly to keep knowledge fresh:

```python
# Daily for active agents
if agent.activity_level == "high":
    reflection_frequency = timedelta(hours=6)
# Weekly for inactive agents
else:
    reflection_frequency = timedelta(days=7)
```

### 2. Focused Reflection

Focus reflection on specific topics:

```python
# Reflect only on code-related memories
await reflect(
    focus="code",
    filters={"tags": ["code", "programming", "bug"]}
)
```

### 3. Quality Over Quantity

Prioritize high-confidence reflections:

```python
# Only store high-quality insights
if reflection.confidence >= 0.8:
    await store_reflection(reflection, layer="semantic")
elif reflection.confidence >= 0.95:
    await store_reflection(reflection, layer="ltm")
```

### 4. Archive Old Reflections

Remove outdated reflections:

```python
@celery.task
def archive_outdated_reflections():
    """Archive reflections that are no longer relevant."""

    old_reflections = await get_reflections(
        age_days=30,
        confidence_below=0.5
    )

    for ref in old_reflections:
        await archive_reflection(ref.id)
```

## Performance Considerations

### Cost Optimization

Reflection uses LLM API calls:

```python
# Estimate cost before reflection
memories_count = 50
avg_tokens_per_memory = 100
total_tokens = memories_count * avg_tokens_per_memory
estimated_cost = total_tokens * 0.00001  # GPT-4 pricing

if estimated_cost > budget:
    # Reduce memory count or use cheaper model
    memories_count = int(budget / (avg_tokens_per_memory * 0.00001))
```

### Caching

Cache reflection results:

```python
# Check cache first
cache_key = f"reflection:{tenant_id}:{hash(memories)}"
cached = await redis.get(cache_key)

if cached:
    return json.loads(cached)

# Generate new reflection
reflection = await generate_reflection(memories)

# Cache for 1 hour
await redis.setex(cache_key, 3600, json.dumps(reflection))
```

## Monitoring

### Reflection Metrics

Track reflection engine performance:

```python
# Metrics to monitor
metrics = {
    "reflections_generated_total": 1523,
    "average_confidence": 0.87,
    "processing_time_seconds": 4.2,
    "memories_processed": 45,
    "insights_stored": 12,
    "insights_rejected": 3,  # Low confidence
}
```

### Quality Monitoring

Monitor reflection quality:

```python
@app.post("/v1/reflection/feedback")
async def provide_feedback(reflection_id: str, helpful: bool):
    """User feedback on reflection quality."""

    await record_feedback(reflection_id, helpful)

    # Adjust future reflections based on feedback
    if not helpful:
        reflection = await get_reflection(reflection_id)
        await adjust_reflection_params(reflection.category)
```

## Troubleshooting

### Low Confidence Reflections

If reflections consistently have low confidence:

1. **Increase memory count**: More evidence = higher confidence
2. **Improve memory quality**: Better tagging and metadata
3. **Adjust prompt**: More specific instructions to LLM
4. **Use better model**: GPT-4 > GPT-3.5

### Slow Reflection

If reflection is too slow:

1. **Reduce memory count**: Process fewer memories
2. **Use faster model**: GPT-3.5 > GPT-4
3. **Parallel processing**: Analyze memories in batches
4. **Optimize prompts**: Shorter prompts = faster processing

### Irrelevant Insights

If reflections aren't useful:

1. **Add focus filters**: Target specific memory types
2. **Improve memory tagging**: Better categorization
3. **Adjust confidence threshold**: Only high-quality insights
4. **Refine prompts**: More specific instructions

## Examples

### Example 1: Code Quality Reflection

```python
# Reflect on code-related memories
reflection = await client.generate_reflection(
    filters={"tags": ["code", "bug", "refactor"]},
    focus="code_quality_patterns",
    memory_limit=30
)

# Result
{
    "content": "The authentication module requires refactoring due to repeated bugs in session handling and token validation",
    "confidence": 0.92,
    "category": "code_quality",
    "evidence": ["mem_12", "mem_34", "mem_56", ...],
    "actionable": True,
    "priority": "high"
}
```

### Example 2: User Preference Learning

```python
# Learn user preferences over time
reflection = await client.generate_reflection(
    filters={"tags": ["user_action", "preference"]},
    focus="user_behavior",
    memory_limit=50
)

# Result
{
    "content": "User prefers dark mode, uses Vim keybindings, and typically works on code between 9 AM - 5 PM EST",
    "confidence": 0.88,
    "category": "user_preference",
    "applications": ["ui_settings", "editor_config", "notification_timing"]
}
```

## Further Reading

- [Memory Layers](memory-layers.md) - Understanding memory architecture
- [Knowledge Graph](graphrag.md) - How reflections connect
- [Scoring Heuristics](../advanced/scoring_heuristics.md) - Confidence calculation

---

**Next**: [Knowledge Graph (GraphRAG) →](graphrag.md)
