from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Configuration settings for the Memory Pack Manager.
    """

    RAE_API_URL: str = "http://localhost:8000"
    RAE_API_KEY: str = "your-rae-api-key"
    RAE_TENANT_ID: str = "default-tenant"  # Default tenant for memory packs

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
