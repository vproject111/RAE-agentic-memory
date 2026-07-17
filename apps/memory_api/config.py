import os
import socket
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuration settings for the Memory API service.
    Settings are loaded from environment variables and/or a .env file.
    """

    POSTGRES_HOST: str = "rae-am-postgres"
    POSTGRES_DB: str = "rae"
    POSTGRES_USER: str = "rae"
    POSTGRES_PASSWORD: str = "rae_password"
    DATABASE_URL: str | None = None

    QDRANT_HOST: str = "rae-am-qdrant"
    QDRANT_PORT: int = 6333
    QDRANT_URL: str | None = None

    RERANKER_API_URL: str = "http://rae-am-reranker:8001"
    ML_SERVICE_URL: str = "http://rae-am-reranker:8001"
    MEMORY_API_URL: str = "http://rae-am-api:8000"

    LLM_MODEL: str | None = None
    GEMINI_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None

    # --- Intelligence & Determinism Stack ---
    # RAE_EMBEDDING_BACKEND: "onnx" ensures 100% deterministic vectors using local models (22MB/130MB)
    RAE_EMBEDDING_BACKEND: str = "onnx"

    # RAE_LLM_MODEL_DEFAULT: Using Qwen 3.5 9B for high-quality synthesis.
    RAE_LLM_MODEL_DEFAULT: str = "ollama/qwen2.5:1.5b"

    # RAE_REFLECTION_STRATEGY:
    # "math" - Purely deterministic L1-L3 reflections
    # "hybrid" - Math for validation + LLM for "Lessons Learned" generation
    RAE_REFLECTION_STRATEGY: str = "hybrid"

    OLLAMA_API_BASE: str | None = None
    OLLAMA_API_URL: str | None = "http://ollama-dev:11434"

    # Ollama Configuration
    OLLAMA_HOSTS: list[str] = [
        "http://ollama-dev:11434",
    ]
    RAE_LLM_BACKEND: str = "ollama"
    RAE_EMBEDDING_MODEL: str | None = None
    RAE_MCP_EMBEDDING_TOOL: str = "get_embedding"
    RAE_MCP_SERVER_COMMAND: str = "python"
    RAE_MCP_SERVER_ARGS: list[str] = []
    EXTRACTION_MODEL: str = "gpt-4o-mini"
    SYNTHESIS_MODEL: str = "gpt-4o"
    RAE_VECTOR_BACKEND: str = "qdrant"
    RAE_RERANKER_BACKEND: str = "emerald"
    RAE_RERANKER_API_URL: str | None = None
    RAE_RERANKER_API_KEY: str | None = None
    RAE_RERANKER_MCP_TOOL: str = "rerank_memories"
    ONNX_EMBEDDER_PATH: str | None = None
    RAE_USE_GPU: bool = False

    @model_validator(mode="after")
    def validate_vector_backend(self):
        if os.getenv("VECTOR_STORE_BACKEND") and not os.getenv("RAE_VECTOR_BACKEND"):
            self.RAE_VECTOR_BACKEND = str(os.getenv("VECTOR_STORE_BACKEND"))
        return self

    RAE_DB_MODE: str = "migrate"
    RAE_PROFILE: str = "standard"

    # --- Security Settings ---
    OAUTH_ENABLED: bool = True
    OAUTH_DOMAIN: str = ""
    OAUTH_AUDIENCE: str = ""
    TENANCY_ENABLED: bool = True
    DEFAULT_TENANT_ALIAS: str = "default-tenant"
    DEFAULT_TENANT_UUID: str = "00000000-0000-0000-0000-000000000000"
    API_KEY: str = "secret"

    ENABLE_API_KEY_AUTH: bool = False
    ENABLE_JWT_AUTH: bool = False
    SECRET_KEY: str = "change-this-secret-key-in-production"

    ENABLE_RATE_LIMITING: bool = False
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60
    ENABLE_COST_TRACKING: bool = False

    ALLOWED_ORIGINS: list[str] = ["*"]

    CELERY_BROKER_URL: str = "redis://rae-am-redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://rae-am-redis:6379/2"
    REDIS_URL: str = "redis://rae-am-redis:6379/0"

    MEMORY_RETENTION_DAYS: int = 30
    MEMORY_DECAY_RATE: float = 0.01
    MEMORY_IMPORTANCE_DECAY_ENABLED: bool = True
    MEMORY_IMPORTANCE_DECAY_RATE: float = 0.01
    MEMORY_IMPORTANCE_DECAY_SCHEDULE: str = "0 2 * * *"
    MEMORY_IMPORTANCE_FLOOR: float = 0.01
    MEMORY_IMPORTANCE_ACCELERATED_THRESHOLD_DAYS: int = 30
    MEMORY_IMPORTANCE_PROTECTED_THRESHOLD_DAYS: int = 7

    LOG_LEVEL: str = "WARNING"
    RAE_APP_LOG_LEVEL: str = "INFO"
    OTEL_TRACES_ENABLED: bool = False

    REFLECTIVE_MEMORY_ENABLED: bool = True
    REFLECTIVE_MEMORY_MODE: str = "full"
    REFLECTIVE_MAX_ITEMS_PER_QUERY: int = 5
    REFLECTIVE_LESSONS_TOKEN_BUDGET: int = 1024

    ENABLE_MATH_V3: bool = True
    MATH_V3_W1_RELEVANCE: float = 0.40
    MATH_V3_W2_IMPORTANCE: float = 0.20
    MATH_V3_W3_RECENCY: float = 0.10
    MATH_V3_W4_CENTRALITY: float = 0.10
    MATH_V3_W5_DIVERSITY: float = 0.10
    MATH_V3_W6_DENSITY: float = 0.10

    ENABLE_SMART_RERANKER: bool = False
    RAE_RERANKER_MODE: str = os.getenv("RAE_RERANKER_MODE", "math")
    RERANKER_MODEL_PATH: str | None = None
    RERANKER_TIMEOUT_MS: int = 10
    RERANKER_TOP_K_CANDIDATES: int = 50
    RERANKER_FINAL_K: int = 10

    ENABLE_FEEDBACK_LOOP: bool = False
    FEEDBACK_POSITIVE_DELTA: float = 0.05
    FEEDBACK_NEGATIVE_DELTA: float = 0.05

    MEMORY_BASE_DECAY_RATE: float = 0.001
    MEMORY_ACCESS_COUNT_BOOST: bool = True
    MEMORY_MIN_DECAY_RATE: float = 0.0001
    MEMORY_MAX_DECAY_RATE: float = 0.01

    REFLECTION_MIN_IMPORTANCE_THRESHOLD: float = 0.3
    REFLECTION_GENERATE_ON_ERRORS: bool = True
    REFLECTION_GENERATE_ON_SUCCESS: bool = False

    DREAMING_ENABLED: bool = False
    DREAMING_LOOKBACK_HOURS: int = 24
    DREAMING_MIN_IMPORTANCE: float = 0.6
    DREAMING_MAX_SAMPLES: int = 20

    SUMMARIZATION_ENABLED: bool = True
    SUMMARIZATION_MIN_EVENTS: int = 10
    SUMMARIZATION_EVENT_THRESHOLD: int = 100

    @model_validator(mode="after")
    def validate_sandbox_mode(self):
        if self.RAE_PROFILE == "lite":

            def is_port_in_use(port):
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    return s.connect_ex(("localhost", port)) == 0

            if is_port_in_use(8000):
                if self.MEMORY_API_URL == "http://localhost:8000":
                    self.MEMORY_API_URL = "http://localhost:8010"
        return self

    @model_validator(mode="after")
    def validate_sandbox_mode(self):
        """
        Detect if RAE and RAE-Lite are co-existing on the same machine.
        If port 8000 is occupied and we are in lite mode, force sandbox ports.
        """
        if self.RAE_PROFILE == "lite":
            import socket

            def is_port_in_use(port):
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    return s.connect_ex(("localhost", port)) == 0

            # If standard RAE is detected, switch to sandbox defaults if not already set
            if is_port_in_use(8000):
                # We don't overwrite explicitly set env vars, but we can log it
                # and adjust default URLs used by internal components
                if self.MEMORY_API_URL == "http://localhost:8000":
                    self.MEMORY_API_URL = "http://localhost:8010"

                # Force sandbox ports for infrastructure if they are still at standard defaults
                if self.POSTGRES_HOST == "localhost":
                    self.POSTGRES_HOST = "localhost"  # Host stays same
                # Ports are usually handled by docker-compose, but we ensure internal URLs are consistent
        return self

    @model_validator(mode="after")
    def apply_mode_overrides(self):
        if self.REFLECTIVE_MEMORY_MODE == "lite":
            self.REFLECTION_GENERATE_ON_SUCCESS = False
            self.DREAMING_ENABLED = False
            self.REFLECTIVE_MAX_ITEMS_PER_QUERY = 3
            self.REFLECTIVE_LESSONS_TOKEN_BUDGET = 512
        elif self.REFLECTIVE_MEMORY_MODE == "full":
            self.REFLECTION_GENERATE_ON_SUCCESS = True
            self.DREAMING_ENABLED = True
            self.REFLECTIVE_MAX_ITEMS_PER_QUERY = 5
            self.REFLECTIVE_LESSONS_TOKEN_BUDGET = 1024
        return self

    model_config = SettingsConfigDict(
        env_file=[
            ".env",
            str(Path(__file__).parent.parent.parent / "rae-core" / ".env"),
            str(Path("/app/rae_core/.env")),
        ],
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
