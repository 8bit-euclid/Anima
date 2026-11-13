import os
import shutil
import subprocess
import sys

from anima.diagnostics import logger
from anima.utils.project import get_project_root_path, get_script_path


class SubprocessManager:
    """Manages the Blender subprocess lifecycle. Handles starting, checking if running, and cleaning up the Blender process."""

    def __init__(self, headless: bool = False):
        """
        Initialize the subprocess manager.

        Args:
            headless (bool): Run Blender without a UI (`--background`), exiting with a non-zero code if the script fails.
        """
        self._headless = headless
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
            # Construct the PYTHONPATH for the subprocess
            env["PYTHONPATH"] = os.pathsep.join(filter(None, [script_dir, src_dir, env.get("PYTHONPATH")]))
            # Prevent Blender's bundled Python from picking up a user-site numpy/scipy
            # (e.g. ~/.local/lib/python3.13/site-packages) that can shadow the pinned versions
            env["PYTHONNOUSERSITE"] = "1"
            _configure_viewport_gpu(env)

            logger.info(f"Starting Blender from: {bl_path}")
            logger.info(f"Running main script from: {script_path}")
            self._subprocess = subprocess.Popen(
                [
                    str(bl_path),
                    *(["--background", "--python-exit-code", "1"] if self._headless else ["--window-maximized"]),
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


def _configure_viewport_gpu(env: dict[str, str]) -> None:
    """Request NVIDIA for Blender's Linux graphics context unless explicitly opted out."""
    selection = env.get("ANIMA_VIEWPORT_GPU", "nvidia").strip().lower()
    if selection not in ("nvidia", "system"):
        raise ValueError(f"ANIMA_VIEWPORT_GPU must be 'nvidia' or 'system', got {selection!r}")
    if selection == "system" or not sys.platform.startswith("linux"):
        return
    if (
        env.get("__NV_PRIME_RENDER_OFFLOAD", "1") != "1"
        or env.get("__GLX_VENDOR_LIBRARY_NAME", "nvidia") != "nvidia"
        or "DRI_PRIME" in env
    ):
        raise RuntimeError(
            "Existing GPU environment settings conflict with NVIDIA selection. "
            "Remove them or set ANIMA_VIEWPORT_GPU=system to opt out."
        )

    nvidia_smi = shutil.which("nvidia-smi")
    if nvidia_smi is None:
        raise RuntimeError("NVIDIA GPU detection unavailable: nvidia-smi was not found")
    try:
        result = subprocess.run(
            [nvidia_smi, "--query-gpu=index", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"NVIDIA GPU detection failed: {exc}") from exc
    if result.returncode != 0 or not result.stdout.strip():
        raise RuntimeError(f"No usable NVIDIA GPU detected: {result.stderr.strip() or 'no devices reported'}")
    env["__NV_PRIME_RENDER_OFFLOAD"] = "1"
    env["__GLX_VENDOR_LIBRARY_NAME"] = "nvidia"
    logger.info("Requesting NVIDIA PRIME offload for Blender graphics")
