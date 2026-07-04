"""
RAE-Lite Main Entry Point.

Starts local HTTP server and system tray app.
"""

import sys
import threading
import time

import structlog
import uvicorn

from rae_lite.config import settings
from rae_lite.server import app
from rae_lite.tray import RAETrayApp

# Setup logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger(__name__)


class ServerThread(threading.Thread):
    """Thread to run FastAPI server."""

    def __init__(self):
        super().__init__(daemon=True)
        self.server = None

    def run(self):
        """Run the server."""
        logger.info(
            "starting_server",
            host=settings.server_host,
            port=settings.server_port,
        )

        config = uvicorn.Config(
            app,
            host=settings.server_host,
            port=settings.server_port,
            log_level="info",
        )
        self.server = uvicorn.Server(config)
        self.server.run()

    def stop(self):
        """Stop the server."""
        if self.server:
            logger.info("stopping_server")
            self.server.should_exit = True


def main():
    """Main entry point for RAE-Lite."""
    logger.info(
        "starting_rae_lite",
        version=settings.app_version,
        data_dir=str(settings.data_dir),
    )

    # 0. Load YAML config if exists
    yaml_config = Path("config.yaml")
    if yaml_config.exists():
        settings.load_from_yaml(yaml_config)
        logger.info("yaml_config_loaded", path=str(yaml_config))

    # Ensure data directory exists
    settings.ensure_data_dir()
    
    # 1. Hardware-Aware Adaptation
    settings.load_profile()
    
    # If no profile was saved yet, run detection and UI
    profile_file = settings.data_dir / "profile.json"
    if not profile_file.exists():
        from rae_lite.hardware import HardwareDetector
        from rae_lite.ui.profile_selector import select_profile
        
        logger.info("first_run_detected_performing_hardware_probe")
        detector = HardwareDetector()
        hw_info = detector.detect_all()
        
        selected = select_profile(hw_info)
        if selected:
            settings.save_profile(selected)
            logger.info("profile_selected", profile=selected)
        else:
            # User cancelled, default to A
            settings.save_profile("A")
            logger.info("profile_fallback_to_A")

    # Start HTTP server in background thread
    server_thread = ServerThread()
    server_thread.start()

    from rae_lite.service import RAELiteService
    # Use data_dir from settings (might be changed by yaml load)
    service = RAELiteService(storage_path=str(settings.data_dir))
    
    # Start service components
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(service.start())

    logger.info(
        "server_started",
        url=f"http://{settings.server_host}:{settings.server_port}",
    )

    # Run system tray (blocks until quit)
    try:
        tray_app = RAETrayApp(server_thread, service)
        tray_app.run()
    except KeyboardInterrupt:
        logger.info("keyboard_interrupt")
    finally:
        # Cleanup
        logger.info("shutting_down")
        server_thread.stop()
        server_thread.join(timeout=5)

    logger.info("rae_lite_stopped")
    sys.exit(0)


if __name__ == "__main__":
    main()
