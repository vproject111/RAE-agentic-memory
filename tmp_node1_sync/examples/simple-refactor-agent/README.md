# Simple Refactor Agent

This is a minimal, working example of an agent that uses the RAE (Reflective Agentic Memory) Engine to perform a code refactoring task.

## How it works

1.  The agent is given a file path and a refactoring instruction (e.g., "rename variable 'x' to 'index'").
2.  It reads the content of the target file.
3.  It constructs a prompt that includes the refactoring instruction and the file content.
4.  It sends this prompt to the RAE Agent's `/agent/execute` endpoint.
5.  The RAE agent uses its memory to get relevant context (e.g., coding style guides, previous refactoring examples) and calls an LLM to perform the refactoring.
6.  The script receives the refactored code and overwrites the original file.

## Prerequisites

Before running this agent, you should store some relevant context in your RAE instance. For example, store a memory with your team's coding conventions:

```bash
curl -X POST "http://localhost:8000/memory/store" \
-H "Content-Type: application/json" \
-H "X-API-Key: your-rae-api-key" \
-H "X-Tenant-Id: refactor-agent-tenant" \
-d '{
  "content": "Python Coding Conventions: Use descriptive variable names. For loops, use `index` for counters, and singular nouns for items (e.g., `for user in users`).",
  "source": "manual/coding_conventions.md",
  "layer": "ltm",
  "tags": ["python", "style-guide"]
}'
```

## Usage

1.  Install the dependencies:
    ```bash
    pip install -r requirements.txt
    ```

2.  Create a sample file to refactor, e.g., `sample_code.py`.

3.  Run the agent:
    ```bash
    python main.py "sample_code.py" "Rename the variable 'x' to 'i' and 'itm' to 'item'."
    ```
