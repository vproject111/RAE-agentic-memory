# RAE LLM Backends

The RAE Memory Engine features a pluggable architecture for Large Language Models, allowing you to easily switch between different providers.

## Core Supported Providers

RAE has explicit support for the following providers, with dedicated provider classes:
- **OpenAI** (`openai`)
- **Google Gemini** (`gemini`)
- **Anthropic** (`anthropic`)
- **Ollama** (`ollama`) for local and open-source models.

## Using Any LiteLLM Provider (Generic Backend)

Beyond the core providers, RAE can interface with **any LLM provider supported by the `litellm` library**. This gives you access to over 100 LLM providers out-of-the-box.

To use a generic `litellm` provider, you simply set the `RAE_LLM_BACKEND` to the name `litellm` uses for that provider, and then provide the model name and the necessary API key.

### How it Works
When `RAE_LLM_BACKEND` is set to a value other than the core providers, RAE uses a generic `LiteLLMProvider`. This provider passes the model and parameters directly to `litellm`. You are responsible for setting the correct API key as an environment variable, using the name `litellm` expects.

### Example 1: Using Mistral
To use Mistral's `mistral-large-latest` model:

1.  Set the environment variables in your `.env` file:
    ```dotenv
    # .env
    RAE_LLM_BACKEND=mistral
    RAE_LLM_MODEL_DEFAULT=mistral/mistral-large-latest
    MISTRAL_API_KEY=your-mistral-api-key
    ```

2.  That's it! `litellm` will automatically use the Mistral provider and authenticate with your API key.

### Example 2: Using DeepSeek
To use DeepSeek's `deepseek/deepseek-chat` model:

1.  Set the environment variables:
    ```dotenv
    # .env
    RAE_LLM_BACKEND=deepseek
    RAE_LLM_MODEL_DEFAULT=deepseek/deepseek-chat
    DEEPSEEK_API_KEY=your-deepseek-api-key
    ```

### Example 3: Using Qwen (Alibaba Cloud)
To use Qwen's `qwen/qwen-long` model:

1.  Set the environment variables:
    ```dotenv
    # .env
    RAE_LLM_BACKEND=qwen
    RAE_LLM_MODEL_DEFAULT=qwen/qwen-long
    DASHSCOPE_API_KEY=your-dashscope-api-key
    ```
    *(Note: `litellm` uses `DASHSCOPE_API_KEY` for Qwen)*

### Example 4: Using Bielik (via Ollama)
Bielik is a Polish model. The easiest way to run it is with Ollama.

1.  Pull the model in Ollama:
    ```bash
    ollama pull bielik
    ```

2.  Set the environment variables to use the `ollama` backend:
    ```dotenv
    # .env
    RAE_LLM_BACKEND=ollama
    RAE_LLM_MODEL_DEFAULT=bielik
    OLLAMA_API_URL=http://localhost:11434  # Or your Ollama instance URL
    ```

### Example 5: Using an OpenAI-Compatible Endpoint

Many open-source models or smaller providers expose an API that is compatible with OpenAI's API. `litellm` can easily call these.

For example, if you are serving a `bielik` model locally with a server that mimics the OpenAI API at `http://localhost:1234/v1`:

1.  Set `RAE_LLM_BACKEND` to `"openai"`. `litellm` treats any unknown backend name as a potential custom litellm provider.
2.  Set `RAE_LLM_MODEL_DEFAULT` to the name the local server expects, e.g. `"bielik"`.
3.  Set the `OPENAI_API_BASE` (or `LITELLM_API_BASE`) environment variable to your local server's address.
4.  Set a dummy API key if your server requires one.

```dotenv
# .env
RAE_LLM_BACKEND=openai
RAE_LLM_MODEL_DEFAULT=bielik
LITELLM_API_BASE=http://localhost:1234/v1
OPENAI_API_KEY=any-string-will-do
```

## Adding a New Model Cost
If you use a new model, you can add its cost to `apps/memory_api/cost_model.py` to ensure accurate cost tracking.

1.  Open the `cost_model.py` file and add an entry to the `MODEL_COSTS` dictionary. The costs are per million tokens (input/output).
    ```python
    # In cost_model.py
    MODEL_COSTS = {
        # ... existing models
        "mistral/mistral-large-latest": {"input": 8.0, "output": 24.0},
    }
    ```

2.  The cost tracking system will now recognize your new model.
