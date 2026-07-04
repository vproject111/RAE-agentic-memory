"""
RAE-Lite Configuration.
"""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """RAE-Lite settings."""

    # App info
    app_name: str = "RAE-Lite"
    app_version: str = "0.1.0"

    # Server
    server_host: str = "127.0.0.1"
    server_port: int = 8765

    # Storage paths
    data_dir: Path = Path.home() / ".rae-lite" / "data"
    db_path: Path = data_dir / "rae_memory.db"
    vector_db_path: Path = data_dir / "rae_vectors.db"
    graph_db_path: Path = data_dir / "rae_graph.db"

    # Memory engine
    enable_reflections: bool = True
    enable_auto_consolidation: bool = True

    # UI
    show_notifications: bool = True
    auto_start: bool = False

    class Config:
        env_prefix = "RAE_LITE_"
        case_sensitive = False

    def ensure_data_dir(self) -> None:
        """Create data directory if it doesn't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_data_dir()
