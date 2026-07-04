from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Configuration settings for the MCP Server.
    """

    RAE_API_URL: str = "http://localhost:8000"
    RAE_API_KEY: str = "your-rae-api-key"  # Default placeholder

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
