# Orchestrator - Quick Start Guide

## ✅ Requirements

### 1. Claude API Key (optional, but recommended)
```bash
# In .env file (already configured):
ANTHROPIC_API_KEY=sk-ant-api03-...
```

### 2. Gemini CLI (free, already installed)
```bash
# Check version:
gemini --version  # ✅ 0.20.0

# If not logged in, log in:
gemini auth login  # Opens browser for authentication
```

## 🚀 Verification - Does the Orchestrator Work?

```bash
cd orchestrator
python test_simple.py
```

**Expected output:**
```
🎉 All tests passed! Orchestrator is ready to use.
Passed: 4/4
```

## 📋 How to Use the Orchestrator?

### Option 1: Example Task from YAML

Create a task file in `.orchestrator/tasks.yaml`:

```yaml
tasks:
  - id: TEST-001
    goal: "Write a simple Python function to calculate factorial"
    description: |
      Create a recursive factorial function with:
      - Input validation (only non-negative integers)
      - Docstring with examples
      - Type hints
      - Unit tests
    risk: low
    area: test
    complexity: small
```

Run:
```bash
cd orchestrator
python main.py --task-id TEST-001
```

### Option 2: Directly from CLI

```bash
cd orchestrator
python cli.py execute \
  --goal "Add logging to the factorial function" \
  --risk low \
  --area test
```

### Option 3: Programmatically (Python API)

```python
import asyncio
from orchestrator.main import Orchestrator
from orchestrator.core.state_machine import TaskDefinition, TaskRisk

async def main():
    # Create the orchestrator
    orchestrator = Orchestrator()

    # Define the task
    task = TaskDefinition(
        task_id="TEST-001",
        goal="Write a function to check if a number is prime",
        description="Simple prime checker with tests",
        risk=TaskRisk.LOW,
        area="test",
    )

    # Execute
    result = await orchestrator.execute_task(task)

    print(f"Status: {result.status}")
    print(f"Cost: ${result.total_cost_usd:.4f}")

asyncio.run(main())
```

## 🔧 Model Configuration

### File: `.orchestrator/providers.yaml`

```yaml
providers:
  # Claude - Paid, but best for critical tasks
  claude:
    enabled: true
    default_model: claude-sonnet-4-5-20250929
    settings:
      api_key: ${ANTHROPIC_API_KEY}

  # Gemini - FREE via CLI!
  gemini:
    enabled: true
    default_model: gemini-2.5-flash
    settings:
      cli_path: gemini
      rate_limit_delay: true  # Important for versions without API key
      min_delay: 1.0
      max_delay: 10.0

routing:
  # Prefer cheaper models when quality is sufficient
  prefer_local: false
  max_cost_per_task: 1.0
  fallback_provider: claude
```

## 💰 Cost Strategies

### 1. **Maximum Savings** (90% of tasks on Gemini)
```yaml
# Gemini for everything except critical tasks
gemini:
  enabled: true
  default_model: gemini-2.5-flash  # Fastest, free

# Claude only for high-risk
routing:
  max_cost_per_task: 0.10  # Max $0.10 per task
```

### 2. **Balanced** (70% Gemini, 30% Claude)
```yaml
# Default configuration
# Gemini: low/medium risk
# Claude: high risk, critical areas
```

### 3. **Maximum Quality** (Claude for everything)
```yaml
claude:
  enabled: true
  default_model: claude-opus-4-20250514  # Best

gemini:
  enabled: false  # Disable Gemini
```

## 📊 Smart Routing - How It Works?

The orchestrator automatically selects the model based on:

### 1. **Task Risk** (3 levels)
```python
TaskRisk.LOW     → Gemini 2.5 Flash Lite  (FREE)
TaskRisk.MEDIUM  → Gemini 2.5 Pro         (FREE)
TaskRisk.HIGH    → Claude Sonnet 4.5      ($0.003/1K)
```

### 2. **Task Area** (where in the code)
```python
area = "core"        → Claude (critical code)
area = "api"         → Gemini Pro
area = "tests"       → Gemini Flash
area = "docs"        → Gemini Flash Lite
```

### 3. **Historical Performance** (learning)
After ~200 tasks, the orchestrator knows:
- Which models are best for a given task type
- Where savings can be made without losing quality
- Which tasks require review

## 🎯 Usage Examples

### Example 1: Simple Test (Free - Gemini)
```bash
cd orchestrator
python cli.py execute \
  --goal "Write tests for user authentication" \
  --risk low \
  --area tests

# Cost: $0.00 (Gemini FREE)
# Time: ~2-3 min
```

### Example 2: Critical Function (Paid - Claude)
```bash
python cli.py execute \
  --goal "Implement memory pruning algorithm" \
  --risk high \
  --area core \
  --complexity medium

# Cost: ~$0.05-0.15 (Claude Sonnet)
# Time: ~5-10 min
# Quality: Maximum
```

### Example 3: Batch Processing (Mix)
```yaml
# tasks.yaml
tasks:
  - id: BATCH-001
    goal: "Add logging to all services"
    risk: low

  - id: BATCH-002
    goal: "Update API documentation"
    risk: low

  - id: BATCH-003
    goal: "Fix memory leak in graph service"
    risk: high

# Run all:
python main.py --batch
```

**Cost:**
- BATCH-001 + BATCH-002: $0.00 (Gemini)
- BATCH-003: $0.10 (Claude)
- **Total: $0.10**

## 🔍 Monitoring

### 1. Run Logs
Each run is saved in `ORCHESTRATOR_RUN_LOG.md`:
```markdown
## Run #42 - 2025-12-10 18:00:00
Task: Add caching to API
Status: SUCCESS
Cost: $0.05
Duration: 8m 23s
```

### 2. Performance Dashboard
```bash
cd orchestrator/intelligence
python dashboard.py summary
```

Output:
```
📊 Overall Statistics
Total executions: 156
Success rate: 94.2%
Average cost: $0.03
Total cost saved: $12.45 (vs all-Claude)

🏆 Top Performers
1. gemini-2.5-flash: 92% success, $0.00 avg
2. claude-sonnet-4-5: 98% success, $0.05 avg
```

### 3. RAE Memory Integration (future)
```python
# The orchestrator will save its experience in RAE
# Then it can learn from previous runs
```

## ⚠️ Important Notes

### Rate Limiting (Gemini Free)
Gemini CLI without an API key has limits:
- **Per-second**: ~2-3 requests/s
- **Per-day**: ~1500 requests/day

The orchestrator automatically adds random delays (1-10s) between requests.

### If You Need More
```bash
# Option 1: Gemini API Key (paid)
export GOOGLE_API_KEY=...
# In providers.yaml:
gemini:
  settings:
    api_key: ${GOOGLE_API_KEY}
    rate_limit_delay: false  # Disable delays

# Option 2: Use Claude only
gemini:
  enabled: false
```

## 🐛 Troubleshooting

### Problem: "Gemini CLI not available"
```bash
# Log in:
gemini auth login

# Check:
gemini --version
```

### Problem: "ANTHROPIC_API_KEY not found"
```bash
# Check .env:
grep ANTHROPIC_API_KEY .env

# Or export:
export ANTHROPIC_API_KEY=sk-ant-...
```

### Problem: Rate limit errors (429)
```yaml
# Increase delays in providers.yaml:
gemini:
  settings:
    min_delay: 5.0   # Was 1.0
    max_delay: 20.0  # Was 10.0
```

## 📖 Further Reading

- `README.md` - Full documentation
- `docs/ORCHESTRATOR_PHASE2.5_COMPLETE.md` - Provider system
- `docs/ORCHESTRATOR_PHASE3_COMPLETE.md` - Intelligence & learning
- `docs/ORCHESTRATOR_MODELS_UPDATE.md` - Models and rate limiting

---

**First steps:**
1. ✅ Run `test_simple.py` - check if it works
2. 🎯 Create a simple task in `tasks.yaml`
3. 🚀 Run `python main.py --task-id YOUR-TASK`
4. 📊 See results in `ORCHESTRATOR_RUN_LOG.md`
5. 💰 Check cost (most tasks = $0.00!)
