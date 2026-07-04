# File Watcher for RAE-Lite.
# Monitors directories and triggers ingestion automatically.

import time
import logging
from pathlib import Path
from typing import Callable, List
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logger = logging.getLogger(__name__)

class RAEFileEventHandler(FileSystemEventHandler):
    def __init__(self, callback: Callable[[Path], None], patterns: List[str] = None):
        self.callback = callback
        self.patterns = patterns or ["*"]

    def on_created(self, event):
        if not event.is_directory:
            self.callback(Path(event.src_path))

    def on_modified(self, event):
        if not event.is_directory:
            self.callback(Path(event.src_path))

class DirectoryWatcher:
    def __init__(self, watch_dir: str, callback: Callable[[Path], None]):
        self.watch_dir = watch_dir
        self.callback = callback
        self.observer = Observer()
        self.handler = RAEFileEventHandler(callback)

    def start(self):
        logger.info(f"Starting watcher on {self.watch_dir}")
        self.observer.schedule(self.handler, self.watch_dir, recursive=True)
        self.observer.start()

    def stop(self):
        self.observer.stop()
        self.observer.join()
