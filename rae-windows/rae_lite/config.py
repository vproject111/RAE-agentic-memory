"""
RAE-Lite Configuration.
"""

from pathlib import Path
import sys
from typing import Optional
import structlog

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = structlog.get_logger(__name__)

class Settings(BaseSettings):
    """
    RAE-Lite Desktop Settings.
    Environment variables prefixed with RAE_LITE_ take precedence.
    """
    app_name: str = "RAE-Lite"
    app_version: str = "1.0.0"

    # Server configuration
    server_host: str = "127.0.0.1"
    server_port: int = 8010
    
    # Storage
    data_dir: Path = Path.home() / ".rae-lite"
    
    # Memory engine
    enable_reflections: bool = True
    enable_auto_consolidation: bool = True

    # Hardware & LLM
    selected_profile: str = "A"  # A, B, C, D
    llama_path: Path = Path.home() / ".rae-lite" / "bin" / ("llama-cli.exe" if "win" in sys.platform else "llama-cli")
    model_path: Optional[Path] = None
    
    # UI
    show_notifications: bool = True
    auto_start: bool = False

    model_config = SettingsConfigDict(
        env_prefix="RAE_LITE_",
        case_sensitive=False
    )


    def ensure_data_dir(self) -> None:
        """Create data directory if it doesn't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def load_from_yaml(self, yaml_path: Path) -> None:
        """Load settings from a YAML file."""
        if not yaml_path.exists():
            return
        
        import yaml
        try:
            with open(yaml_path, "r") as f:
                data = yaml.safe_load(f)
                if not data:
                    return
                
                # Map YAML structure to settings
                if "system" in data:
                    self.app_name = data["system"].get("app_name", self.app_name)
                if "storage" in data:
                    if "data_dir" in data["storage"]:
                        self.data_dir = Path(data["storage"]["data_dir"])
                if "observer" in data:
                    # In service.py RAELiteService takes enable_observer as param
                    # but we can store it here too
                    pass
        except Exception as e:
            from structlog import get_logger
            get_logger(__name__).error("failed_to_load_yaml_config", error=str(e))

    def load_profile(self) -> None:
        """Load profile from data directory if exists."""
        profile_file = self.data_dir / "profile.json"
        if profile_file.exists():
            import json
            try:
                data = json.loads(profile_file.read_text())
                self.selected_profile = data.get("profile", "A")
                if "model_path" in data:
                    self.model_path = Path(data["model_path"])
            except Exception:
                pass

    def save_profile(self, profile: str, model_path: Optional[str] = None) -> None:
        """Save selected profile to data directory."""
        import json
        self.selected_profile = profile
        if model_path:
            self.model_path = Path(model_path)
        
        profile_file = self.data_dir / "profile.json"
        data = {"profile": profile}
        if self.model_path:
            data["model_path"] = str(self.model_path)
            
        profile_file.write_text(json.dumps(data))


settings = Settings()
settings.ensure_data_dir()
