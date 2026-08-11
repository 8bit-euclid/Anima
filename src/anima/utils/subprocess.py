import os
import subprocess

from anima.diagnostics import logger
from anima.utils.project import get_project_root_path, get_script_path


class SubprocessManager:
    """Manages the Blender subprocess lifecycle. Handles starting, checking if running, and cleaning up the Blender process."""

    def __init__(self):
        self._subprocess: subprocess.Popen | None = None

    def start(self) -> bool:
        """Start a new Blender process.
        Returns:
            bool: True if the subprocess was started successfully, False otherwise.
        """
        try:
            from anima.utils.blender import get_blender_executable_path

            bl_path = get_blender_executable_path()
            script_path = get_script_path()

            # Set up the environment for the subprocess
            env = os.environ.copy()
            src_dir = str(get_project_root_path() / "src")
            script_dir = str(script_path.parent)  # so sibling modules next to the script are importable
            env["PYTHONPATH"] = os.pathsep.join(filter(None, [script_dir, src_dir, env.get("PYTHONPATH")]))

            logger.info(f"Starting Blender from: {bl_path}")
            logger.info(f"Running main script from: {script_path}")
            self._subprocess = subprocess.Popen(
                [
                    str(bl_path),
                    "--window-maximized",
                    "--factory-startup",
                    "--python-use-system-env",  # Required for Blender to honor PYTHONPATH
                    "--python",
                    str(script_path),
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Merge stderr into stdout
                text=True,
                bufsize=1,
                start_new_session=True,  # isolate Blender from parent
                env=env,  # so any script, in or out of this repo, can `import anima`
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
                    logger.warning("Subprocess didn't terminate gracefully, forcing kill")
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
