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

    # Ensure data directory exists
    settings.ensure_data_dir()

    # Start HTTP server in background thread
    server_thread = ServerThread()
    server_thread.start()

    # Give server time to start
    time.sleep(2)

    logger.info(
        "server_started",
        url=f"http://{settings.server_host}:{settings.server_port}",
    )

    # Run system tray (blocks until quit)
    try:
        tray_app = RAETrayApp(server_thread)
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
