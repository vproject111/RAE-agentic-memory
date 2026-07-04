from typing import Any

from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer


class FileChangeHandler(PatternMatchingEventHandler):
    """
    Handles file system events and triggers a callback.
    It ignores git files and pycache.
    """

    def __init__(
        self,
        callback,
        patterns=None,
        ignore_patterns=None,
        ignore_directories=True,
        case_sensitive=False,
    ):
        if patterns is None:
            patterns = [
                "*.py",
                "*.js",
                "*.ts",
                "*.md",
                "*.txt",
                "*.json",
                "*.yaml",
                "*.yml",
            ]

        # Add more git-related patterns to ignore
        if ignore_patterns is None:
            ignore_patterns = [
                "*/.git/*",
                "*/__pycache__/*",
                "*/.idea/*",
                "*/.vscode/*",
                "*.log",
            ]

        super().__init__(
            patterns=patterns,
            ignore_patterns=ignore_patterns,
            ignore_directories=ignore_directories,
            case_sensitive=case_sensitive,
        )
        self.callback = callback

    def on_modified(self, event):
        """Called when a file is modified."""
        print(f"File modified: {event.src_path}")
        self.callback(event.src_path)

    def on_created(self, event):
        """Called when a file is created."""
        print(f"File created: {event.src_path}")
        self.callback(event.src_path)


def start_watching(path: str, callback) -> Any:
    """
    Starts a file system observer for a given path.

    Args:
        path: The directory path to watch.
        callback: The function to call when a file is changed.

    Returns:
        The observer instance.
    """
    event_handler = FileChangeHandler(callback)
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    print(f"Watcher started for path: {path}")
    return observer
