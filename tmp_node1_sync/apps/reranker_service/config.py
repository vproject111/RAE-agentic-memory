from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Configuration settings for the Reranker Service.
    Settings are loaded from environment variables and/or a .env file.
    """

    # No specific settings for the reranker service yet, but this is here for future use.

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
