from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Configuration settings for the Simple Refactor Agent.
    """

    RAE_API_URL: str = "http://localhost:8000"
    RAE_API_KEY: str = "your-rae-api-key"
    RAE_TENANT_ID: str = "refactor-agent-tenant"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
