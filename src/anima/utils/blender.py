import bpy
import functools
from pathlib import Path
from time import sleep
from anima.diagnostics import logger
from anima.utils.project import get_pyproject_config_value
from anima.utils.subprocess import SubprocessManager
from anima.utils.input import BlenderInputMonitor
from anima.utils.output import BlenderOutputMonitor


class BlenderProcess:
    """Main facade class that coordinates all Blender operations."""

    def __init__(self, script_path: Path = None):
        self._subproc_manager = SubprocessManager(script_path)
        self._input_monitor = BlenderInputMonitor()
        self._output_monitor = BlenderOutputMonitor()

    def start(self):
        """Start Blender and run the main.py script."""
        try:
            if self._subproc_manager.running():
                logger.info(
                    f"Found running Blender instance (pid: {self._subproc_manager.subprocess.pid})")
                # TODO
            else:
                if not self._subproc_manager.start():
                    raise RuntimeError("Failed to start Blender subprocess")
                self._input_monitor._configure_blender()

        except Exception as e:
            logger.error(f"Error running script: {e}")
            self._subproc_manager.cleanup()
            raise

    def monitor(self):
        """Monitor Blender with keyboard shortcuts."""
        subproc = self._subproc_manager.subprocess
        if not subproc:
            logger.error("No Blender process to monitor")
            return

        # Start input/output monitoring
        self._input_monitor.start()
        self._output_monitor.start(subproc)

        # # Define callbacks for keyboard events
        # def on_reload():
        #     logger.info("Reloading script...")
        #     if self._script_reloader.reload():
        #         logger.info("✓ Script reloaded successfully")
        #     else:
        #         logger.error("✗ Failed to reload script")

        # def on_quit():
        #     self._cleanup()

        # # Start keyboard monitoring
        # self._keyboard_monitor.start(on_reload, on_quit)

        # sleep(3)
        # self.reload()
        # self.quit()

        try:
            # Wait for Blender process to end
            logger.info("Blender is running")
            subproc.wait()
            logger.info(f"Blender process has ended")

        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt: Terminating Blender...")

        finally:
            self._input_monitor.stop()
            self._output_monitor.stop()
            self._subproc_manager.cleanup()

    def reload(self):
        """Reload the main script in Blender."""
        self._input_monitor.reload_main()

    def quit(self):
        """Quit Blender gracefully."""
        self._input_monitor.quit_blender()


@functools.lru_cache(maxsize=1)
def get_blender_root_path() -> Path:
    """Get the root path of the Blender executable from pyproject.toml.
    Returns:
        Path: The root path of the Blender executable.
    Raises:
        FileNotFoundError: If Blender path does not exist.
    """
    bl_config = get_pyproject_config_value('tool.blender')
    root_dir = Path(bl_config.get('root-dir', '')).expanduser()
    if not root_dir.exists():
        raise FileNotFoundError(f"Blender path does not exist: {root_dir}")
    return root_dir


@functools.lru_cache(maxsize=1)
def get_blender_executable_path() -> Path:
    """Get Blender executable path from project config.
    Returns:
        Path: The path to the Blender executable.
    Raises:
        FileNotFoundError: If Blender path does not exist.
    """
    # Get the Blender executable path
    bl_path = get_blender_root_path() / 'blender'
    if not bl_path.exists():
        raise FileNotFoundError(f"Blender path does not exist: {bl_path}")
    return bl_path


def configure_blender_viewport():
    """Configure the Blender 3D viewport to top view."""
    # Find and activate the 3D viewport
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                for region in area.regions:
                    if region.type == 'WINDOW':
                        logger.debug("Found 3D viewport: overriding context")
                        override = {
                            'area': area,
                            'region': region,
                            'space_data': area.spaces.active if hasattr(area.spaces, "active") else area.spaces[0]
                        }
                        with bpy.context.temp_override(**override):
                            if bpy.ops.view3d.view_axis.poll():
                                bpy.ops.view3d.view_axis(type='TOP')
                                logger.debug("Set 3D viewport to top view")
                        break
                break
        else:
            continue
        break
