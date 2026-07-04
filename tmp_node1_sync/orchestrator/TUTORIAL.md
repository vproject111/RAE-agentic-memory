# Tutorial - First Steps with Orchestrator

## 🎯 Goal
Learn to use the orchestrator in 5 minutes.

---

## Step 1: Check if it works (30 seconds)

```bash
cd orchestrator
python test_simple.py
```

**Expected output:**
```
🎉 All tests passed! Orchestrator is ready to use.
Passed: 4/4
```

✅ If you see this - you can continue!
❌ If an error - check QUICK_START.md "Troubleshooting" section

---

## Step 2: See available tasks (10 seconds)

```bash
cd ..  # Go back to the main project directory
cat .orchestrator/tasks.yaml
```

**Available examples:**
- `TEST-001` - Add docstrings (simple, **FREE** - Gemini)
- `TEST-002` - Add tests (medium, **FREE** - Gemini Pro)
- `RAE-PHASE2-001` - Core implementation (hard, **$0.10-0.20** - Claude)
- `RAE-API-001` - REST endpoint (medium, **FREE** - Gemini Pro)

---

## Step 3A: Run a SIMPLE task (RECOMMENDED for the first time)

### Add a NEW simple task to `.orchestrator/tasks.yaml`:

```yaml
  # Your first task - very simple!
  - id: MY-FIRST-001
    goal: "Write a simple hello_world() function in Python"
    risk: low
    area: test
    repo: RAE-agentic-memory
    constraints:
      - Add docstring
      - Add type hints
      - Return greeting string
```

### Run:

```bash
cd orchestrator
python main.py --task-id MY-FIRST-001
```

**What will happen:**
1. Orchestrator will load the task from YAML
2. Smart routing will select **Gemini 2.5 Flash** (FREE!)
3. Planner will create an implementation plan
4. Implementer will write the code
5. Reviewer will check quality
6. Results saved in `ORCHESTRATOR_RUN_LOG.md`

**Time:** ~2-3 minutes
**Cost:** $0.00 (Gemini FREE)

---

## Step 3B: Run an EXISTING task

```bash
cd orchestrator
python main.py --task-id TEST-001
```

This will add docstrings to `ContextBuilder` - a simple, free task.

---

## Step 4: See results

### Main logs:
```bash
cat ../ORCHESTRATOR_RUN_LOG.md | tail -100
```

### Task status:
```bash
cat state/MY-FIRST-001.json | jq .
# or without jq:
cat state/MY-FIRST-001.json
```

### Summary:
```bash
python cli.py summary
```

Output:
```
📊 Orchestrator Summary

Total Tasks: 1
Active Tasks: 0
Needs Human Review: 0
Total Cost: $0.00
```

---

## Step 5: Add your own task

### Edit `.orchestrator/tasks.yaml`:

```yaml
  - id: MY-TASK-001
    goal: "Your task description..."
    risk: low       # low, medium, high
    area: test      # test, docs, api, core
    repo: RAE-agentic-memory
    context_files:  # Optional - files to read
      - path/to/file.py
    constraints:    # Requirements
      - ZERO-WARNINGS
      - Add tests
```

### Run:
```bash
cd orchestrator
python main.py --task-id MY-TASK-001
```

---

## 💡 Tips

### 1. **Selecting Risk Level:**
```yaml
risk: low     # Gemini Flash Lite → FREE
risk: medium  # Gemini Pro → FREE
risk: high    # Claude Sonnet → ~$0.05-0.15 (paid)
```

### 2. **Selecting Area:**
```yaml
area: docs    # Documentation → Gemini Flash Lite (fastest, FREE)
area: tests   # Tests → Gemini Flash (FREE)
area: api     # API → Gemini Pro (FREE)
area: core    # Core logic → Claude Sonnet (paid, but best)
```

### 3. **Batch Processing (multiple tasks at once):**
```bash
# Run all tasks from the file
cd orchestrator
python main.py
```

This will execute **all** tasks from `tasks.yaml` sequentially.

### 4. **Monitoring:**
```bash
# See active tasks
cd orchestrator
python cli.py summary

# See tasks requiring review
python cli.py review
```

---

## 🎓 Example: Practical Workflow

### Scenario: Add a feature to RAE

**1. Plan tasks in YAML:**
```yaml
tasks:
  # Step 1: Documentation (free)
  - id: FEATURE-001-DOCS
    goal: "Document new caching strategy in API_DOCS.md"
    risk: low
    area: docs

  # Step 2: Implementation (free)
  - id: FEATURE-002-IMPL
    goal: "Implement Redis caching layer"
    risk: medium
    area: api

  # Step 3: Tests (free)
  - id: FEATURE-003-TESTS
    goal: "Add integration tests for caching"
    risk: medium
    area: tests
```

**2. Run all:**
```bash
cd orchestrator
python main.py
```

**3. See results:**
```bash
python cli.py summary
cat ../ORCHESTRATOR_RUN_LOG.md | tail -200
```

**Total Cost:** $0.00 (all on Gemini!)
**Time:** ~10-15 minutes total

---

## ❓ FAQ

**Q: Do I need an API key for Claude?**
A: NO - most tasks (70-80%) work on Gemini (FREE). Claude is only needed for high-risk tasks.

**Q: How to reduce costs?**
A: Set `risk: low` or `risk: medium` - it will use free Gemini.

**Q: What if a task fails?**
A: Check logs in `ORCHESTRATOR_RUN_LOG.md`. The orchestrator has retry logic (3 attempts).

**Q: Can I run a task without YAML?**
A: Not directly, but you can use the Python API (example in QUICK_START.md).

**Q: How to disable Claude and use only Gemini?**
A: In `.orchestrator/providers.yaml` set `claude: enabled: false`

---

## 🚀 Next Steps

1. ✅ Run `MY-FIRST-001` - simple test task
2. ✅ See results in logs
3. ✅ Add your own task to YAML
4. ✅ Experiment with different `risk` and `area`
5. 📖 Read `QUICK_START.md` for advanced options

---

**Need help?**
- `orchestrator/QUICK_START.md` - Complete guide
- `orchestrator/README.md` - Full documentation
- `docs/ORCHESTRATOR_PHASE2.5_COMPLETE.md` - Provider system
- `docs/ORCHESTRATOR_PHASE3_COMPLETE.md` - Intelligence & learning

**Ready to automate?** 🤖
