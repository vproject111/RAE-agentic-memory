# Local LLM Setup Guide (Ollama)

This guide explains how to run RAE with a local LLM using Ollama. This setup allows for offline development, cost savings, and privacy.

## 1. Prerequisites

- **Docker & Docker Compose**: Ensure you have the latest version.
- **Hardware**: 
  - Minimum: 8GB RAM (for small models like `deepseek-coder:1.3b` or `qwen:1.8b`).
  - Recommended: NVIDIA GPU (if available, configure `nvidia-container-toolkit` for faster inference).
  - **Current Dev Setup**: Configured for CPU execution by default to ensure compatibility.

## 2. Starting RAE with Local LLM

RAE uses Docker Compose profiles to keep the default environment lightweight. To enable Ollama, you must specify the `local-llm` profile.

### Command

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml --profile local-llm up -d
```

This starts the `rae-ollama` container on port `11434`.

## 3. Downloading Models

Before the first use, you must pull the desired model into the container.

### Recommended Models for Dev (CPU-friendly)
- **DeepSeek Coder 1.3B**: Fast, good for code logic.
  ```bash
  docker exec -it rae-ollama ollama pull deepseek-coder:1.3b
  ```
- **Qwen 1.8B**: Good general purpose small model.
  ```bash
  docker exec -it rae-ollama ollama pull qwen:1.8b
  ```

### Standard Models (Requires good CPU or GPU)
- **DeepSeek LLM 7B**:
  ```bash
  docker exec -it rae-ollama ollama pull deepseek-llm:7b
  ```

## 4. Configuring RAE to use Ollama

### Option A: Full Switch (All RAE traffic goes to Ollama)
Update your `.env` file:

```dotenv
# .env

# 1. Select the backend
RAE_LLM_BACKEND=ollama

# 2. Configure URL (use 'ollama' hostname inside docker network, or 'localhost' if running RAE locally)
OLLAMA_API_URL=http://localhost:11434 

# 3. Select the model you pulled
RAE_LLM_MODEL_DEFAULT=deepseek-coder:1.3b
```

### Option B: Hybrid / Multi-Agent (Orchestrator)
You can use a powerful cloud model (Gemini/Claude) for complex tasks and Ollama for cheaper/simpler tasks (like code review).

Update `.orchestrator/providers.yaml`:

```yaml
providers:
  claude:
    enabled: true
    default_model: claude-3-opus-20240229
  
  ollama:
    enabled: true
    default_model: deepseek-coder:1.3b
    settings:
      api_url: http://localhost:11434

routing:
  overrides:
    # Route code reviews to local LLM to save cost
    code_review: 
      provider: ollama
      model: deepseek-coder:1.3b
    
    # Route complex reasoning to cloud
    complex_reasoning:
      provider: claude
```

## 5. Troubleshooting

- **"Connection Refused"**: Ensure the `rae-ollama` container is running (`docker ps`).
- **Slow Performance**: 
  - Check if you are running on CPU.
  - Switch to a smaller model (e.g., from 7B to 1.3B).
  - If you have an NVIDIA GPU, uncomment the `deploy` section in `docker-compose.dev.yml` to enable GPU acceleration.

## 6. How to Disable

Simply run docker compose without the profile:
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --remove-orphans
```
