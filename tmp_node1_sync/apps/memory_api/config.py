import os

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuration settings for the Memory API service.
    Settings are loaded from environment variables and/or a .env file.
    """

    POSTGRES_HOST: str = "localhost"
    POSTGRES_DB: str = "rae"
    POSTGRES_USER: str = "rae"
    POSTGRES_PASSWORD: str = "rae_password"
    DATABASE_URL: str | None = None

    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_URL: str | None = None

    RERANKER_API_URL: str = "http://localhost:8001"
    ML_SERVICE_URL: str = "http://localhost:8001"
    MEMORY_API_URL: str = "http://localhost:8000"

    LLM_MODEL: str | None = None
    GEMINI_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    OLLAMA_API_BASE: str = "http://rae-ollama:11434"
    OLLAMA_API_URL: str = "http://rae-ollama:11434"
    # Ollama Configuration
    OLLAMA_HOSTS: list[str] = ["http://100.66.252.117:11434", "http://rae-ollama:11434"]
    RAE_LLM_BACKEND: str = "ollama"
    RAE_LLM_MODEL_DEFAULT: str = "ollama/deepseek-coder:1.3b"
    EXTRACTION_MODEL: str = "gpt-4o-mini"
    SYNTHESIS_MODEL: str = "gpt-4o"
    RAE_VECTOR_BACKEND: str = "qdrant"
    ONNX_EMBEDDER_PATH: str | None = None

    @model_validator(mode="after")
    def validate_vector_backend(self):
        """Backward compatibility: Support legacy VECTOR_STORE_BACKEND variable"""
        if os.getenv("VECTOR_STORE_BACKEND") and not os.getenv("RAE_VECTOR_BACKEND"):
            self.RAE_VECTOR_BACKEND = str(os.getenv("VECTOR_STORE_BACKEND"))
        return self

    # Database Validation Mode
    # migrate: Run migrations automatically on startup (default for DX)
    # validate: Check schema and fail fast on mismatch (safe for prod)
    # init: Initialize empty DB (same as migrate)
    # ignore: Skip validation
    RAE_DB_MODE: str = "migrate"

    # RAE Profile (standard, lite, research)
    # standard: Full infrastructure (DB, Redis, Qdrant)
    # lite: Minimal dependencies (Memory/Mock implementations where possible)
    # research: Specialized for experiments
    RAE_PROFILE: str = "standard"

    # --- Security Settings ---
    OAUTH_ENABLED: bool = True
    OAUTH_DOMAIN: str = ""  # e.g., "your-tenant.us.auth0.com"
    OAUTH_AUDIENCE: str = ""  # e.g., "https://yourapi.com"
    TENANCY_ENABLED: bool = True
    DEFAULT_TENANT_ALIAS: str = "default-tenant"
    DEFAULT_TENANT_UUID: str = "00000000-0000-0000-0000-000000000000"
    API_KEY: str = "secret"

    # Authentication
    ENABLE_API_KEY_AUTH: bool = False  # Set to True in production
    ENABLE_JWT_AUTH: bool = False  # Set to True when using JWT tokens
    SECRET_KEY: str = "change-this-secret-key-in-production"  # For JWT signing

    # Rate Limiting
    ENABLE_RATE_LIMITING: bool = False  # Set to True in production
    RATE_LIMIT_REQUESTS: int = 100  # Max requests per window
    RATE_LIMIT_WINDOW: int = 60  # Time window in seconds
    ENABLE_COST_TRACKING: bool = False  # Set to True to track request costs

    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8501"]

    # --- LLM Provider API Keys ---
    # These are loaded from environment variables automatically by pydantic-settings.
    # Add any new provider keys here for awareness, even if not defined as a field.
    #
    # MISTRAL_API_KEY: str | None = None
    # DEEPSEEK_API_KEY: str | None = None
    # DASHSCOPE_API_KEY: str | None = None (for Qwen)

    # Celery settings
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Memory lifecycle settings
    MEMORY_RETENTION_DAYS: int = 30
    MEMORY_DECAY_RATE: float = 0.01  # 1% decay per day (legacy)

    # Memory importance decay settings (Phase 3 - Enterprise)
    MEMORY_IMPORTANCE_DECAY_ENABLED: bool = True  # Enable importance-based decay
    MEMORY_IMPORTANCE_DECAY_RATE: float = 0.01  # 1% decay per day for importance scores
    MEMORY_IMPORTANCE_DECAY_SCHEDULE: str = "0 2 * * *"  # Cron: daily at 2 AM
    MEMORY_IMPORTANCE_FLOOR: float = (
        0.01  # Minimum importance score (prevents complete decay)
    )
    MEMORY_IMPORTANCE_ACCELERATED_THRESHOLD_DAYS: int = 30  # Days for accelerated decay
    MEMORY_IMPORTANCE_PROTECTED_THRESHOLD_DAYS: int = 7  # Days for protected decay

    # Logging configuration
    LOG_LEVEL: str = "WARNING"  # For external libraries (uvicorn, asyncpg, etc.)
    RAE_APP_LOG_LEVEL: str = "INFO"  # For RAE application logs
    OTEL_TRACES_ENABLED: bool = False  # For OpenTelemetry tracing

    # ============================================================================
    # Reflective Memory V1 Configuration (RAE Implementation Plan)
    # ============================================================================

    # Feature flags
    REFLECTIVE_MEMORY_ENABLED: bool = True  # Enable reflective memory system
    REFLECTIVE_MEMORY_MODE: str = "full"  # "lite" or "full"

    # Retrieval limits
    REFLECTIVE_MAX_ITEMS_PER_QUERY: int = 5  # Max reflections per context
    REFLECTIVE_LESSONS_TOKEN_BUDGET: int = 1024  # Max tokens for lessons learned

    # Scoring configuration
    MEMORY_SCORE_WEIGHTS_ALPHA: float = 0.5  # Relevance weight (similarity)
    MEMORY_SCORE_WEIGHTS_BETA: float = 0.3  # Importance weight
    MEMORY_SCORE_WEIGHTS_GAMMA: float = 0.2  # Recency weight

    # Hybrid Math V3 Configuration
    ENABLE_MATH_V3: bool = True  # Enable Hybrid Math v3 scoring (Iteration 1)
    MATH_V3_W1_RELEVANCE: float = 0.40
    MATH_V3_W2_IMPORTANCE: float = 0.20
    MATH_V3_W3_RECENCY: float = 0.10
    MATH_V3_W4_CENTRALITY: float = 0.10
    MATH_V3_W5_DIVERSITY: float = 0.10
    MATH_V3_W6_DENSITY: float = 0.10

    # Iteration 2: Smart Re-Ranker
    ENABLE_SMART_RERANKER: bool = False  # Enable ML-based re-ranking
    # RAE_RERANKER_MODE: 'math' (default) or 'llm' (requires LLM service)
    RAE_RERANKER_MODE: str = os.getenv("RAE_RERANKER_MODE", "math")
    RERANKER_MODEL_PATH: str | None = None
    RERANKER_TIMEOUT_MS: int = 10
    RERANKER_TOP_K_CANDIDATES: int = 50
    RERANKER_FINAL_K: int = 10

    # Iteration 3: Feedback Loop
    ENABLE_FEEDBACK_LOOP: bool = False  # Enable learning from feedback
    FEEDBACK_POSITIVE_DELTA: float = 0.05
    FEEDBACK_NEGATIVE_DELTA: float = 0.05

    # Decay configuration
    MEMORY_BASE_DECAY_RATE: float = 0.001  # Base decay rate per second
    MEMORY_ACCESS_COUNT_BOOST: bool = True  # Consider access count in decay
    MEMORY_MIN_DECAY_RATE: float = 0.0001  # Minimum decay rate
    MEMORY_MAX_DECAY_RATE: float = 0.01  # Maximum decay rate

    # Reflection generation
    REFLECTION_MIN_IMPORTANCE_THRESHOLD: float = 0.3  # Min importance to store
    REFLECTION_GENERATE_ON_ERRORS: bool = True  # Generate on errors
    REFLECTION_GENERATE_ON_SUCCESS: bool = False  # Generate on success (lite mode off)

    # Dreaming configuration (batch reflection)
    DREAMING_ENABLED: bool = False  # Enable dreaming in lite mode
    DREAMING_LOOKBACK_HOURS: int = 24  # Hours to look back
    DREAMING_MIN_IMPORTANCE: float = 0.6  # Min importance for dreaming
    DREAMING_MAX_SAMPLES: int = 20  # Max memories per cycle

    # Summarization configuration
    SUMMARIZATION_ENABLED: bool = True  # Enable session summarization
    SUMMARIZATION_MIN_EVENTS: int = 10  # Min events to trigger
    SUMMARIZATION_EVENT_THRESHOLD: int = 100  # Threshold for long sessions

    # Mode-specific overrides
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
        """Apply configuration based on lite/full mode"""
        if self.REFLECTIVE_MEMORY_MODE == "lite":
            # Lite mode: minimal overhead
            self.REFLECTION_GENERATE_ON_SUCCESS = False
            self.DREAMING_ENABLED = False
            self.REFLECTIVE_MAX_ITEMS_PER_QUERY = 3
            self.REFLECTIVE_LESSONS_TOKEN_BUDGET = 512
        elif self.REFLECTIVE_MEMORY_MODE == "full":
            # Full mode: all features
            self.REFLECTION_GENERATE_ON_SUCCESS = True
            self.DREAMING_ENABLED = True
            self.REFLECTIVE_MAX_ITEMS_PER_QUERY = 5
            self.REFLECTIVE_LESSONS_TOKEN_BUDGET = 1024
        return self

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
