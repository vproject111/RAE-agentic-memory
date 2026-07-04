# Ollama Wrapper

The RAE-Ollama Wrapper allows you to integrate your local Ollama LLMs with the RAE Memory Engine, providing them with long-term, structured memory.

## How it Works

The wrapper acts as a proxy:

1.  You send a prompt to the wrapper.
2.  The wrapper queries the RAE Memory API for relevant context.
3.  It constructs a new, context-enriched prompt.
4.  It sends this prompt to your local Ollama instance.
5.  Ollama processes the prompt and streams the response back.
6.  The wrapper streams the response back to you.

## Setup

1.  **Install Ollama**: Follow the instructions on [ollama.ai](https://ollama.ai/) to install Ollama and download your desired models (e.g., `ollama pull llama3`).
2.  **Configure RAE API**: Ensure your RAE Memory API is running and accessible.
3.  **Configure Wrapper**:
    Create a `.env` file in the `integrations/ollama-wrapper/` directory:

    ```
    RAE_API_URL="http://localhost:8000"
    RAE_API_KEY="your-secret-rae-api-key"
    OLLAMA_API_URL="http://localhost:11434" # Or your Ollama host:port
    RAE_TENANT_ID="my-ollama-project"
    ```

## Usage

1.  Navigate to the wrapper directory:
    ```bash
    cd integrations/ollama-wrapper
    ```
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Run the chat command:
    ```bash
    python main.py chat "What is the capital of France?" --model llama3
    ```

The wrapper will automatically fetch relevant memories from RAE and inject them into the prompt sent to Ollama.
