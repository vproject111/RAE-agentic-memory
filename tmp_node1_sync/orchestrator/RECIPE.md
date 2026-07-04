# 📋 RECIPE - How to Run the Orchestrator Independently

> **Goal:** Run the orchestrator WITHOUT Claude Code assistance to AVOID wasting tokens.

---

## ⚡ QUICK START (2 minutes)

### Step 1: Open Terminal
```bash
# Go to the project directory
# Use dynamic path, assuming script is run from project root or similar context
# Example: cd "$(dirname "$0")/../.." if run from orchestrator/
cd "$PROJECT_ROOT"
```

### Step 2: Activate Environment
```bash
# Activate Python virtual environment
source .venv/bin/activate
```

### Step 3: Run Task
```bash
# Run DEMO-001 (simplest task)
python -m orchestrator.main --task-id DEMO-001
```

**DONE!** 🎉

---

## 📖 DETAILED RECIPE

### Preparation (once, at the beginning)

#### 1. Check if Gemini is working
```bash
# Go to the project root (assuming you are in the project's root when running this)
cd "$PROJECT_ROOT"
source .venv/bin/activate
cd orchestrator
python test_simple.py
```

**Expected outcome:**
```
✅ PASS - Registry
✅ PASS - Gemini Provider
✅ PASS - Generation
✅ PASS - Claude Provider

🎉 All tests passed! Orchestrator is ready to use.
```

If you see this - you can continue!

---

### Method 1: Run an Existing Task

#### Step 1: See available tasks
```bash
# From the project root directory
cd "$PROJECT_ROOT"
cat .orchestrator/tasks.yaml
```

**You will see:**
- `DEMO-001` - Timestamp function (simple, FREE)
- `TEST-001` - Add docstrings (simple, FREE)
- `TEST-002` - Add tests (medium, FREE)
- `RAE-PHASE2-001` - Core implementation (hard, paid ~$0.15)

#### Step 2: Choose task ID
```bash
# For example DEMO-001
TASK_ID="DEMO-001"
```

#### Step 3: Run
```bash
# From the project's root directory
cd "$PROJECT_ROOT"
source .venv/bin/activate
python -m orchestrator.main --task-id $TASK_ID
```

#### Step 4: See results
```bash
# Main log
cat ORCHESTRATOR_RUN_LOG.md | tail -100

# Task status
cat orchestrator/state/${TASK_ID}.json | jq .

# Summary
cd orchestrator
python cli.py summary
```

---

### Method 2: Add Your Own Task

#### Step 1: Edit the tasks file
```bash
nano .orchestrator/tasks.yaml
# or
vim .orchestrator/tasks.yaml
# or
code .orchestrator/tasks.yaml  # VS Code
```

#### Step 2: Add your task
```yaml
  # Add at the end of the file:
  - id: MY-001
    goal: "Your task description here"
    risk: low          # low=free, medium=free, high=paid
    area: test         # test, docs, api, core
    repo: RAE-agentic-memory
    constraints:
      - ZERO-WARNINGS
      - Add docstring
      - Add tests
```

#### Step 3: Save and run
```bash
# Save the file (Ctrl+O in nano, :wq in vim)
# Then run:
python -m orchestrator.main --task-id MY-001
```

---

## 🎛️ CONFIGURATION - Model Selection

### Option A: Gemini Only (FREE - recommended for beginners)

Edit: `.orchestrator/providers.yaml`
```yaml
providers:
  claude:
    enabled: false      # ❌ Disable Claude (paid)

  gemini:
    enabled: true       # ✅ Gemini only (FREE)
    default_model: gemini-2.5-flash
    settings:
      cli_path: gemini
      rate_limit_delay: true
      min_delay: 1.0
      max_delay: 10.0
```

**Cost:** $0.00 for ALL tasks!

---

### Option B: Mix (Smart - Gemini + Claude)

```yaml
providers:
  claude:
    enabled: true       # ✅ For high-risk only
    default_model: claude-sonnet-4-5-20250929

  gemini:
    enabled: true       # ✅ For low/medium risk
    default_model: gemini-2.5-flash
```

Orchestrator will automatically select:
- **low/medium risk** → Gemini (FREE)
- **high risk** → Claude (~$0.05-0.15)

---

### Option C: Claude Only (best quality)

```yaml
providers:
  claude:
    enabled: true
    default_model: claude-sonnet-4-5-20250929

  gemini:
    enabled: false      # ❌ Disable Gemini
```

**Cost:** ~$0.05-0.15 per task (high quality)

---

## 📝 COMPLETE EXAMPLE - Step by Step

### Scenario: Add docstrings to a file

```bash
# 1. Open terminal
cd "$PROJECT_ROOT"

# 2. Activate venv
source .venv/bin/activate

# 3. Check if it works (optional)
cd orchestrator
python test_simple.py
cd ..

# 4. See available tasks
cat .orchestrator/tasks.yaml | grep "id:"

# 5. Select task TEST-001 (add docstrings)
# This task is FREE (uses Gemini)

# 6. Run
python -m orchestrator.main --task-id TEST-001

# Orchestrator will:
# - Load the task
# - Select Gemini (FREE)
# - Create a plan
# - Implement
# - Check quality
# - Save results

# 7. See results
cat ORCHESTRATOR_RUN_LOG.md | tail -100

# 8. Check status
cd orchestrator
python cli.py summary
```

---

## 🐛 TROUBLESHOOTING

### Problem 1: "ModuleNotFoundError: No module named 'orchestrator'"

**Solution:**
```bash
# Make sure you are in the main project directory
cd "$PROJECT_ROOT"

# And use python -m orchestrator.main (not python orchestrator/main.py)
python -m orchestrator.main --task-id DEMO-001
```

---

### Problem 2: "Gemini CLI not available"

**Solution:**
```bash
# Log in to Gemini CLI
gemini auth login

# Check if it works
gemini --version
```

---

### Problem 3: "ANTHROPIC_API_KEY not found" (when using Claude)

**Solution:**
```bash
# Check if the key is in .env
grep ANTHROPIC_API_KEY .env

# If not - add:
echo "ANTHROPIC_API_KEY=sk-ant-api03-..." >> .env

# Or export:
export ANTHROPIC_API_KEY=sk-ant-api03-...
```

---

### Problem 4: Gemini returns parsing error

**Solution 1: Use a simpler task**
```bash
# Instead of a complex one, run DEMO-001
python -m orchestrator.main --task-id DEMO-001
```

**Solution 2: Switch to Claude**
```bash
# Edit .orchestrator/providers.yaml
# Set gemini: enabled: false
# Set claude: enabled: true
```

---

### Problem 5: "Rate limit exceeded" (Gemini)

**Solution:**
```bash
# Increase delays in .orchestrator/providers.yaml:
gemini:
  settings:
    min_delay: 5.0    # Was 1.0
    max_delay: 20.0   # Was 10.0
```

---

## 💰 COST CONTROL

### See how much you've spent:
```bash
cd orchestrator
python cli.py summary
```

Output:
```
Total Cost: $0.00    # If you use Gemini
# or
Total Cost: $2.45    # If you use Claude
```

### See task details:
```bash
cat orchestrator/state/DEMO-001.json | jq '.total_cost_usd'
```

---

## 🚀 ADVANCED USAGE

### Batch Processing (multiple tasks at once)
```bash
# Run all tasks from tasks.yaml
python -m orchestrator.main

# The Orchestrator will execute all tasks sequentially
```

### Only specific tasks:
```bash
# Run TEST-001 and TEST-002
python -m orchestrator.main --task-id TEST-001
python -m orchestrator.main --task-id TEST-002
```

### With custom working directory:
```bash
python -m orchestrator.main \
  --task-id TEST-001 \
  --working-dir /path/to/your/project
```

---

## 📊 MONITORING

### Dashboard (see statistics):
```bash
cd orchestrator/intelligence
python dashboard.py summary
```

### See top performers:
```bash
python dashboard.py rankings
```

### Cost optimizations:
```bash
python dashboard.py optimize
```

---

## ✅ CHECKLIST - First Run

- [ ] I am in the project directory
- [ ] Activated `.venv` (`source .venv/bin/activate`)
- [ ] Test works (`python orchestrator/test_simple.py` - 4/4 passed)
- [ ] Gemini is logged in (`gemini --version`)
- [ ] I selected a task from `tasks.yaml`
- [ ] I am running: `python -m orchestrator.main --task-id XXX`
- [ ] Waiting for results (2-5 minutes)
- [ ] Checking logs: `cat ORCHESTRATOR_RUN_LOG.md`

---

## 🎯 SUMMARY

### What to DO:
✅ Run orchestrator YOURSELF (without Claude Code)
✅ Use Gemini for simple tasks (FREE)
✅ Use Claude for critical tasks (paid)
✅ Check costs: `python cli.py summary`

### What NOT to do:
❌ Do not run via Claude Code (token waste)
❌ Do not use Claude for everything (expensive)
❌ Do not run without rate limiting (Gemini)

---

## 📞 QUICK HELP

**Something not working?**

1. **Basic test:**
   ```bash
   cd orchestrator && python test_simple.py
   ```
   If 4/4 passed = all OK!

2. **Simple generation test:**
   ```bash
   cd orchestrator && python test_direct_generation.py
   ```
   If it returns Python code = Gemini works!

3. **Check configuration:**
   ```bash
   cat .orchestrator/providers.yaml
   ```

4. **See logs:**
   ```bash
   cat ORCHESTRATOR_RUN_LOG.md | tail -200
   ```

---

**READY FOR AUTOMATION? 🤖**

Copy and paste to terminal:
```bash
cd "$PROJECT_ROOT"
source .venv/bin/activate
python -m orchestrator.main --task-id DEMO-001
```

**Cost: $0.00 | Time: 2-3 min | Quality: ✅**
