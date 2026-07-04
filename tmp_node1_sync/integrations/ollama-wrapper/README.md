# RAE-Ollama Wrapper

This tool provides a bridge between Ollama and the RAE (Reflective Agentic Memory) Engine.

It allows you to have conversations with local LLMs running via Ollama, while giving them access to a long-term, structured memory provided by the RAE API.

## How it works

1.  You send a prompt to this wrapper tool.
2.  The wrapper queries the RAE Memory API to find relevant context.
3.  It constructs a new, context-enriched prompt.
4.  It sends the new prompt to the Ollama API.
5.  It streams the response from Ollama back to you.

## Usage

1.  Install the dependencies:
    ```bash
    pip install -r requirements.txt
    ```

2.  Configure the API endpoints in a `.env` file:
    ```
    RAE_API_URL="http://localhost:8000"
    RAE_API_KEY="your-secret-key"
    OLLAMA_API_URL="http://localhost:11434"
    RAE_TENANT_ID="my-project"
    ```

3.  Run the chat interface:
    ```bash
    python main.py chat "Your prompt here" --model llama3
    ```
