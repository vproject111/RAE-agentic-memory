from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Configuration settings for the RAE-Ollama Wrapper.
    Settings are loaded from environment variables and/or a .env file.
    """

    RAE_API_URL: str = "http://localhost:8000"
    RAE_API_KEY: str = "your-rae-api-key"  # Default placeholder
    OLLAMA_API_URL: str = "http://localhost:11434"

    # The tenant ID to use when communicating with the RAE Memory API
    RAE_TENANT_ID: str = "default-tenant"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
