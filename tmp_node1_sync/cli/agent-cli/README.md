# RAE Agent CLI

This is a command-line interface (CLI) to interact with the RAE (Reasoning Agentic-memory Engine) API.

## Multi-Model Backend

It is important to understand that this CLI is a **client** for the RAE API. The choice of which Large Language Model (LLM) is used (e.g., OpenAI's GPT-4o, Anthropic's Claude, Google's Gemini, or a local model via Ollama) is configured on the **backend `memory-api` service**.

To change the model, you need to set the `RAE_LLM_BACKEND` and `RAE_LLM_MODEL_DEFAULT` environment variables for the `memory-api` service (e.g., in your `.env` file) and restart it. Please refer to the `docs/llm_backends.md` file for more details.

## Installation

1.  Install the dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

The CLI is an alias for `python cli/agent-cli/main.py`. You can create a shell alias for convenience, for example:
`alias rae="python cli/agent-cli/main.py"`

### Health Check

Check the health of the API:
```bash
rae health
```

### Add Memory

Add a memory from a string:
```bash
rae memory-add --tenant "my-tenant" --project "my-project" --content "This is a new memory."
```

### Query Memory

Query memories:
```bash
rae memory-query --tenant "my-tenant" "What is this project about?"
```

### Ask Agent

Ask the agent a question:
```bash
rae agent-ask --tenant "my-tenant" --project "my-project" --prompt "Summarize the recent memories."
```
