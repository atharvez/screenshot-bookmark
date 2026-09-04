"""Folder watcher for detecting new screenshots."""
import time
import logging
from pathlib import Path
from typing import Callable, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent

logger = logging.getLogger(__name__)

# Common screenshot file extensions
SCREENSHOT_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.gif'}

class ScreenshotHandler(FileSystemEventHandler):
    """Handles file system events for screenshots."""

    def __init__(self, on_screenshot_detected: Callable[[str], None]):
        """
        Initialize the screenshot handler.

        Args:
            on_screenshot_detected: Callback function called when a screenshot is detected
        """
        self.on_screenshot_detected = on_screenshot_detected
        self.processing_files = set()  # Track files currently being processed

    def on_created(self, event):
        """Handle file creation events."""
        if not event.is_directory:
            self._handle_file_event(event.src_path)

    def on_modified(self, event):
        """Handle file modification events (for incomplete downloads)."""
        if not event.is_directory:
            self._handle_file_event(event.src_path)

    def _handle_file_event(self, file_path: str):
        """Handle a file event if it's a screenshot."""
        # Avoid processing the same file multiple times
        if file_path in self.processing_files:
            return

        path = Path(file_path)
        if path.suffix.lower() in SCREENSHOT_EXTENSIONS:
            # Wait a moment to ensure file is fully written
            def process_file():
                try:
                    self.processing_files.add(file_path)
                    logger.info(f"Screenshot detected: {file_path}")
                    self.on_screenshot_detected(file_path)
                except Exception as e:
                    logger.exception(f"Error processing screenshot {file_path}: {e}")
                finally:
                    self.processing_files.discard(file_path)

            # Process after a short delay to ensure file is ready
            import threading
            timer = threading.Timer(1.0, process_file)
            timer.start()


class FolderWatcher:
    """Watches a folder for new screenshots."""

    def __init__(self, watch_path: str, on_screenshot_detected: Callable[[str], None]):
        """
        Initialize the folder watcher.

        Args:
            watch_path: Path to the folder to watch
            on_screenshot_detected: Callback function called when a screenshot is detected
        """
        self.watch_path = Path(watch_path).expanduser().resolve()
        self.on_screenshot_detected = on_screenshot_detected
        self.observer = Observer()
        self.event_handler = ScreenshotHandler(on_screenshot_detected)

        if not self.watch_path.exists():
            logger.warning(f"Watch path does not exist: {self.watch_path}")
            self.watch_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created watch path: {self.watch_path}")

    def start(self):
        """Start watching the folder."""
        logger.info(f"Starting to watch folder: {self.watch_path}")
        self.observer.schedule(self.event_handler, str(self.watch_path), recursive=False)
        self.observer.start()

    def stop(self):
        """Stop watching the folder."""
        logger.info("Stopping folder watcher")
        self.observer.stop()
        self.observer.join()

    def is_running(self) -> bool:
        """Check if the watcher is running."""
        return self.observer.is_alive()


# Convenience function for simple usage
def watch_folder(watch_path: str, on_screenshot_detected: Callable[[str], None]) -> FolderWatcher:
    """
    Start watching a folder for screenshots.

    Args:
        watch_path: Path to the folder to watch
        on_screenshot_detected: Callback function called when a screenshot is detected

    Returns:
        FolderWatcher instance (call .stop() to stop watching)
    """
    watcher = FolderWatcher(watch_path, on_screenshot_detected)
    watcher.start()
    return watcher