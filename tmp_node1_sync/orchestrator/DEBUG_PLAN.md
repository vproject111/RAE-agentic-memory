# 🔧 Orchestrator Debug Plan

## What I Did (While You Were Away):

### 1. Disabled Project Rules
**File:** `orchestrator/agents/base.py`
```python
def _load_project_rules(self, working_dir: str) -> str:
    # DISABLED: Project rules cause issues with LLM prompts
    return ""
```

**Why:** Rules added ~5-50KB to each prompt, potentially causing issues.

---

### 2. Added Extensive Logging
**File:** `orchestrator/adapters/claude_adapter.py`

Now in every API call you will see:
```
INFO: Claude API call: model=claude-sonnet-4-5-20250929, prompt_len=1234
DEBUG: Prompt preview: Task: Check if file exists...
INFO: Claude API success: input=456, output=123
```

On error:
```
ERROR: Claude API error: ConnectionError: Connection refused
```

---

### 3. Created an Ultra-Simple Test Task
**File:** `.orchestrator/tasks.yaml`

```yaml
- id: TEST-SIMPLE
  goal: "Check if file exists: rae-core/rae_core/context/builder.py"
  risk: low
  area: docs
  repo: RAE-agentic-memory
  constraints:
    - Read file rae-core/rae_core/context/builder.py
    - Report if file exists or not
    - Output: YES or NO
```

This is the simplest possible task - just checking if a file exists.

---

### 4. Added Claude API Test (without orchestrator)
**File:** `orchestrator/test_claude_direct.py`

You can check if Claude works on its own:
```bash
cd orchestrator
source ../.venv/bin/activate
python test_claude_direct.py
```

---

## 🚀 How to Test:

### Test 1: Check if Claude API works
```bash
cd "$PROJECT_ROOT"/orchestrator
source ../.venv/bin/activate
python test_claude_direct.py
```

**Expected outcome:**
```
✅ API key found: sk-ant-api03-...
📤 Prompt: What is 2+2? Answer in one word.
⏳ Calling Claude API...
✅ Success!
📥 Response: Four
```

**If this does NOT work:**
- The problem is with Claude API / key / network
- NOT with the orchestrator

---

### Test 2: Run the simplest orchestrator task
```bash
cd "$PROJECT_ROOT"
source .venv/bin/activate
python -m orchestrator.main --task-id TEST-SIMPLE 2>&1 | tee orchestrator_test_simple.log
```

**This will:**
- Run the orchestrator
- With the simplest possible task
- With extensive logging
- Save everything to `orchestrator_test_simple.log`

---

### Test 3: Log Analysis

After running the orchestrator, you will see in the logs **exactly where it fails**:

**Scenario A: Claude API works**
```
INFO: Claude API call: model=claude-sonnet-4-5-20250929, prompt_len=456
INFO: Claude API success: input=123, output=45
```
→ Problem is in parsing the response or other logic

**Scenario B: Claude API does not work**
```
ERROR: Claude API error: ConnectionError: ...
```
→ Problem with API / key / network

**Scenario C: Something else**
```
ERROR: Task TEST-SIMPLE failed with exception
Traceback ...
```
→ Problem somewhere in the orchestrator before Claude API call

---

## 📝 What to Save:

After running, copy **ALL** logs to:
```
docs/bledy-orkiestrator_04.md
```

Required information:
1. Full output from `python -m orchestrator.main --task-id TEST-SIMPLE`
2. Last lines from `orchestrator_test_simple.log`
3. Whether `test_claude_direct.py` worked

---

## 🔍 What to Check:

### Claude API Key
```bash
grep ANTHROPIC_API_KEY .env
```
Should be: `ANTHROPIC_API_KEY=sk-ant-api03-...`

### Is anthropic package installed
```bash
source .venv/bin/activate
pip show anthropic
```
Should be: `Version: 0.74.1` or higher

### Internet connectivity
```bash
curl -I https://api.anthropic.com
```
Should return: `HTTP/2 200` (or 403, but NOT connection refused)

---

## 💡 Possible Causes of Errors:

### 1. Claude API Key Invalid
**Symptom:** `AuthenticationError` in logs
**Fix:** Check if the key in `.env` is correct

### 2. No Internet / Firewall
**Symptom:** `ConnectionError` in logs
**Fix:** Check connection with `curl https://api.anthropic.com`

### 3. anthropic Package Problem
**Symptom:** `ImportError` or weird errors
**Fix:** `pip install --upgrade anthropic`

### 4. Problem in Orchestrator
**Symptom:** Error BEFORE "Claude API call" in logs
**Fix:** This will need further debugging

### 5. Problem with Response Parsing
**Symptom:** "Claude API success" in logs, but then an error
**Fix:** Problem in agent logic, not in Claude

---

## 🎯 Next Steps:

1. **Run Test 1** (test_claude_direct.py)
   - If ❌ → Problem with Claude API
   - If ✅ → Go to Test 2

2. **Run Test 2** (TEST-SIMPLE via orchestrator)
   - Save ALL logs to docs/bledy-orkiestrator_04.md
   - I will come back and analyze what went wrong

3. **If Test 2 ✅ works:**
   - Try RAE-DOC-001: `python -m orchestrator.main --task-id RAE-DOC-001`
   - If that also works → PROBLEM SOLVED! 🎉

---

## 📊 Status of Changes:

```
✅ Project rules disabled (base.py)
✅ Extensive logging added (claude_adapter.py)
✅ Ultra-simple TEST-SIMPLE task created (.orchestrator/tasks.yaml)
✅ Direct Claude test added (test_claude_direct.py)
✅ Everything committed (commit 5e8aaceb4)
```

---

**You are ready for testing!** 🚀

Run the tests and save the logs. I will analyze them when you return from your walk.
