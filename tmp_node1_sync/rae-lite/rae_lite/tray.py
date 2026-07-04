"""
RAE-Lite System Tray Application.
"""

import sys
import threading
import webbrowser

import structlog
from PIL import Image, ImageDraw
from pystray import Icon, Menu, MenuItem

from rae_lite.config import settings

logger = structlog.get_logger(__name__)


def create_icon_image():
    """Create a simple icon image."""
    # Create a 64x64 image with a gradient
    size = 64
    image = Image.new("RGB", (size, size), color="#2563eb")

    # Draw a simple "R" shape
    draw = ImageDraw.Draw(image)
    draw.text((20, 20), "R", fill="white")

    return image


class RAETrayApp:
    """System tray application for RAE-Lite."""

    def __init__(self, server_thread: threading.Thread):
        """
        Initialize tray app.

        Args:
            server_thread: Thread running the FastAPI server
        """
        self.server_thread = server_thread
        self.icon = None
        self.running = False

    def open_dashboard(self, icon, item):
        """Open dashboard in browser."""
        url = f"http://{settings.server_host}:{settings.server_port}/docs"
        webbrowser.open(url)
        logger.info("dashboard_opened", url=url)

    def open_data_folder(self, icon, item):
        """Open data folder."""
        import subprocess

        if sys.platform == "win32":
            subprocess.run(["explorer", str(settings.data_dir)])
        elif sys.platform == "darwin":
            subprocess.run(["open", str(settings.data_dir)])
        else:
            subprocess.run(["xdg-open", str(settings.data_dir)])

        logger.info("data_folder_opened", path=str(settings.data_dir))

    def show_about(self, icon, item):
        """Show about dialog."""
        # Simple console output for now
        # In production, this would open a proper dialog
        print(f"\n{settings.app_name} v{settings.app_version}")
        print("Local-first AI Memory Desktop App")
        print(f"Server: http://{settings.server_host}:{settings.server_port}")
        print(f"Data: {settings.data_dir}\n")

    def quit_app(self, icon, item):
        """Quit the application."""
        logger.info("quitting_app")
        self.running = False
        icon.stop()
        # Server thread will be stopped by main.py

    def run(self):
        """Run the system tray icon."""
        self.running = True

        # Create menu
        menu = Menu(
            MenuItem(
                "Open Dashboard",
                self.open_dashboard,
                default=True,
            ),
            Menu.SEPARATOR,
            MenuItem("Open Data Folder", self.open_data_folder),
            MenuItem("About", self.show_about),
            Menu.SEPARATOR,
            MenuItem("Quit", self.quit_app),
        )

        # Create and run icon
        self.icon = Icon(
            settings.app_name,
            create_icon_image(),
            f"{settings.app_name} - Running",
            menu,
        )

        logger.info("starting_tray_app")
        self.icon.run()
