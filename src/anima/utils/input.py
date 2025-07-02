import select
import tty
import termios
import sys
import threading
from anima.diagnostics import logger


class BlenderKeyboardMonitor:
    """Monitors keyboard input for Blender control."""

    def __init__(self):
        self._monitoring: bool = False
        self._thread: threading.Thread | None = None

    def start(self, on_reload: callable, on_quit: callable) -> None:
        """Start keyboard monitoring with callbacks."""
        self._monitoring = True

        if sys.platform == "win32":
            self._thread = threading.Thread(
                target=self._handle_keyboard_windows,
                args=(on_reload, on_quit),
                daemon=True
            )
        else:
            self._thread = threading.Thread(
                target=self._handle_keyboard_unix,
                args=(on_reload, on_quit),
                daemon=True
            )

        self._thread.start()

    def stop(self) -> None:
        """Stop keyboard monitoring."""
        self._monitoring = False
        self._thread.join()

    def _handle_keyboard_unix(self, on_reload: callable, on_quit: callable):
        """Handle keyboard input on Unix systems."""
        old_settings = termios.tcgetattr(sys.stdin)
        try:
            tty.setraw(sys.stdin.fileno())

            while self._monitoring:
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    key = sys.stdin.read(1)

                    if key.lower() == 'r':
                        logger.info("Reloading Blender...")
                        on_reload()

                    elif key.lower() == 'q':
                        logger.info("Stopping Blender...")
                        on_quit()
                        break

        except Exception as e:
            logger.error(f"Keyboard handling error: {e}")
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

    def _handle_keyboard_windows(self, on_reload: callable, on_quit: callable):
        """Handle keyboard on Windows."""
        raise NotImplementedError(
            "Windows keyboard handling is not implemented yet."
        )
