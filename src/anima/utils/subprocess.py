import subprocess
from pathlib import Path

from anima.diagnostics import logger
from anima.utils.project import get_main_file_path


class SubprocessManager:
    """Manages the Blender subprocess lifecycle. Handles starting, checking if running, and cleaning up the Blender process."""

    def __init__(self, script_path: Path = None):
        self._subprocess: subprocess.Popen | None = None
        self._script_path: Path = script_path or get_main_file_path()

    def start(self) -> bool:
        """Start a new Blender process.
        Returns:
            bool: True if the subprocess was started successfully, False otherwise.
        """
        try:
            from anima.utils.blender import get_blender_executable_path as bl_path

            logger.info(f"Starting Blender from: {bl_path()}")

            self._subprocess = subprocess.Popen(
                [
                    bl_path(),
                    "--window-maximized",
                    "--factory-startup",
                    "--python",
                    self._script_path,
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Merge stderr into stdout
                text=True,
                bufsize=1,
                start_new_session=True,  # isolate Blender from parent
            )

            logger.info(f"Blender started (pid: {self.subprocess.pid})")
            return True

        except Exception as e:
            logger.error(f"Could not start Blender: {e}")
            self._subprocess = None
            return False

    def running(self) -> bool:
        """Check if process is running.
        Returns:
            bool: True if the subprocess is running, False otherwise.
        """
        return self.subprocess is not None and self.subprocess.poll() is None

    def cleanup(self) -> None:
        """Clean up the process. If the subprocess is running, it will be terminated gracefully. If it does not terminate within 5 seconds, it will be forcefully killed."""
        if self.subprocess:
            try:
                logger.info(f"Terminating subprocess (pid: {self.subprocess.pid})")
                self.subprocess.terminate()

                try:
                    self.subprocess.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning(
                        "Subprocess didn't terminate gracefully, forcing kill"
                    )
                    self.subprocess.kill()
            except (ProcessLookupError, AttributeError):
                pass
            finally:
                self._subprocess = None

    @property
    def subprocess(self) -> subprocess.Popen | None:
        """Get the current process.
        Returns:
            subprocess.Popen | None: The current subprocess if running, None otherwise.
        """
        return self._subprocess
