import subprocess
from pathlib import Path
from anima.diagnostics import logger
from anima.utils.project import get_main_file_path


class SubprocessManager:
    """Manages the Blender subprocess lifecycle."""

    def __init__(self, script_path: Path = None):
        self._process: subprocess.Popen | None = None
        self._script_path: Path = script_path or get_main_file_path()

    def start(self) -> bool:
        """Start a new Blender process."""
        try:
            from anima.utils.blender import get_blender_executable_path as bl_path
            logger.info(f"Starting Blender from: {bl_path()}")

            self._process = subprocess.Popen(
                [bl_path(), '--window-maximized', '--python', self._script_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Merge stderr into stdout
                text=True,
                bufsize=1
            )

            logger.info(f"Blender started (pid: {self.process.pid})")
            return True

        except Exception as e:
            logger.error(f"Could not start Blender: {e}")
            self._process = None
            return False

    def running(self) -> bool:
        """Check if process is running."""
        return (self.process is not None and self.process.poll() is None)

    def cleanup(self) -> None:
        """Clean up the process."""
        if self.process:
            try:
                logger.info(
                    f"Stopping Blender process (pid: {self.process.pid})")
                self.process.terminate()

                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning(
                        "Blender didn't terminate gracefully, forcing kill")
                    self.process.kill()
            except (ProcessLookupError, AttributeError):
                pass
            finally:
                self._process = None

    @property
    def process(self) -> subprocess.Popen | None:
        """Get the current process."""
        return self._process
