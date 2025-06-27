import bpy
import functools
import psutil
import subprocess
import threading
from pathlib import Path
from anima.diagnostics import logger
from anima.utils.project_utils import configure_project_reload, get_main_file_path, get_pyproject_config_value


RELOAD_SCRIPT_PATH = Path(__file__).parent / "scripts" / "reload.py"


class BlenderProcess:
    def __init__(self, script_path=None):
        self._process: subprocess.Popen | None = None
        self._script_path: Path = script_path or get_main_file_path()

    def initialize(self):
        """Start/reload Blender and run the main.py script."""
        try:
            reload = self._check_process_status()
            if reload:
                logger.info(
                    f"Found running Blender instance (pid: {self._process.pid})")
                self._reload_script()
            else:
                self._start_new_process()

        except Exception as e:
            logger.error(f"Error running script: {e}")
            self._cleanup_process()
            raise

        return self

    def monitor(self):
        process = self._process
        if not process:
            logger.error("No Blender process to monitor")
            return self

        try:
            logger.info("Monitoring Blender output... Press Ctrl+C to stop")
            process.wait()  # blocks until Blender exits
            logger.info(f"Blender process has ended (pid: {process.pid})")
        except KeyboardInterrupt:
            pass
        finally:
            self._cleanup_process()
        return self

    # Private interface ------------------------------------------------------------------------------------ #

    def _start_new_process(self):
        """Start a new Blender process with GUI in a separate window and pass main.py as a script.
        Raises:
            FileNotFoundError: If Blender executable is not found.
            subprocess.SubprocessError: If there is an error starting Blender."""
        try:
            # Start Blender with GUI (no --background flag) with main.py as the script and store process.
            bl_path = get_blender_executable_path()
            main_path = get_main_file_path()
            logger.info(f"Starting Blender from: {bl_path}")
            logger.info(f"Using main.py: {main_path}")
            self._process = subprocess.Popen([bl_path, '--window-maximized', '--python', main_path],
                                             stdin=subprocess.PIPE,
                                             stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE,
                                             text=True,
                                             bufsize=1)

            # Check if it's already dead (immediate failure)
            process = self._process
            if process.poll() is not None and process.returncode != 0:
                stderr = process.stderr.read()
                self._process = None
                raise subprocess.SubprocessError(
                    f"Blender failed to start with error: {stderr}"
                )

            # Verify that Blender is running, and start output monitoring
            running = self._check_process_status()
            if running:
                logger.info(f"Blender started (pid: {process.pid})")
                self._start_output_monitoring_threads()
            else:
                logger.error("Blender failed to start")
                self._process = None

        except (FileNotFoundError, subprocess.SubprocessError) as e:
            logger.error(f"Could not start Blender: {e}")
            self._process = None

    def _check_process_status(self) -> bool:
        """Check if Blender is already running.
        Returns:
            bool: True if Blender is running, else False.
        Raises:
            AssertionError: If the stored process PID does not match the running Blender process.
        """
        # First check if we have a stored process and it's still running
        if self._process and self._process.poll() is None:
            return True

        # If no stored process or it's dead, check system processes
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if 'blender' in proc.info['name'].lower():
                    assert self._process.pid == proc.pid, "Cannot handle multiple Blender instances."
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False

    def _start_output_monitoring_threads(self):
        """Start threads to monitor Blender output"""
        if not self._process:
            return []

        def read_stream(stream):
            try:
                while True:
                    line = stream.readline()
                    if not line:  # Empty string means EOF
                        break
                    print(f"{line.rstrip()}")
            except Exception as e:
                logger.error(f"Error reading line: {e}")

        threads = []
        streams = [self._process.stdout, self._process.stderr]
        for stream in streams:
            if stream:  # Check if stream exists
                t = threading.Thread(
                    target=read_stream,
                    args=(stream,),
                    daemon=True
                )
                t.start()
                threads.append(t)

        return threads

    def _reload_script(self):
        """Send reload command to Blender via stdin to reload the main.py script."""
        configure_project_reload()

        process = self._process
        if not process or process.poll() is not None:
            logger.error("Blender process is no longer running")
            return False

        try:
            # Load reload script from external file
            with open(RELOAD_SCRIPT_PATH, 'r') as f:
                template = f.read()

            # Format the script by interpolating to {main_path}.
            # NOTE: Must be named as such in RELOAD_SCRIPT_PATH.
            reload_script = template.format(main_path=get_main_file_path())

            # Send the reload command to Blender
            process.stdin.write(reload_script + '\n')
            process.stdin.flush()
            logger.info(f"Sent reload command to Blender (pid: {process.pid})")
            return True

        except Exception as e:
            logger.error(f"Error sending reload command: {e}")
            return False

    def _cleanup_process(self):
        """Clean up Blender process if we started it."""
        process = self._process
        if process:
            try:
                logger.info(
                    f"Stopping Blender process (pid: {process.pid})")
                process.terminate()

                # Wait for graceful shutdown
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning(
                        "Blender didn't terminate gracefully, forcing kill")
                    process.kill()

            except (ProcessLookupError, AttributeError):
                # Process already terminated
                pass
            finally:
                self._process = None


def configure_blender_viewport():
    # Find and activate the 3D viewport
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                for region in area.regions:
                    if region.type == 'WINDOW':
                        override = {
                            'area': area,
                            'region': region,
                            'space_data': area.spaces.active if hasattr(area.spaces, "active") else area.spaces[0]
                        }
                        logger.debug(
                            "Found 3D viewport. Setting context override...")
                        with bpy.context.temp_override(**override):
                            if bpy.ops.view3d.view_axis.poll():
                                bpy.ops.view3d.view_axis(type='TOP')
                                logger.debug(
                                    "Successfully set 3D viewport to top view")
                        break
                break
        else:
            continue
        break


@functools.lru_cache(maxsize=1)
def get_blender_executable_path() -> Path:
    """Get Blender executable path from project config.
    Returns:
        Path: The path to the Blender executable.
    Raises:
        FileNotFoundError: If Blender path does not exist.
    """
    # Load Blender configuration from pyproject.toml
    blender_cfg = get_pyproject_config_value('tool.blender', {})
    root_dir = Path(blender_cfg.get('root-dir', '')).expanduser()

    # Get the Blender executable path
    bl_path = root_dir / 'blender'
    if not bl_path.exists():
        raise FileNotFoundError(
            f"Blender path does not exist: {bl_path}")
    return bl_path
