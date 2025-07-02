import bpy
import functools
from pathlib import Path
from anima.diagnostics import logger
from anima.utils.project import get_pyproject_config_value
from anima.utils.subprocess import SubprocessManager
from anima.utils.reload import BlenderScriptReloader
from anima.utils.input import BlenderKeyboardMonitor
from anima.utils.output import BlenderOutputMonitor


class BlenderProcess:
    """Main facade class that coordinates all Blender operations."""

    def __init__(self, script_path=None):
        self._subproc_manager = SubprocessManager(script_path)
        self._script_reloader = BlenderScriptReloader(self._subproc_manager)
        self._keyboard_monitor = BlenderKeyboardMonitor()
        self._output_monitor = BlenderOutputMonitor()

    def start(self):
        """Start Blender and run the main.py script."""
        try:
            if self._subproc_manager.running():
                logger.info(
                    f"Found running Blender instance (pid: {self._subproc_manager.process.pid})")
                self._script_reloader.reload()
            else:
                if not self._subproc_manager.start():
                    raise RuntimeError("Failed to start Blender process")
        except Exception as e:
            logger.error(f"Error running script: {e}")
            self._subproc_manager.cleanup()
            raise

    def monitor(self):
        """Monitor Blender with keyboard shortcuts."""
        process = self._subproc_manager.process
        if not process:
            logger.error("No Blender process to monitor")
            return

        # Start output monitoring
        self._output_monitor.start(process)

        # Define callbacks for keyboard events
        def on_reload():
            logger.info("Reloading script...")
            if self._script_reloader.reload():
                logger.info("✓ Script reloaded successfully")
            else:
                logger.error("✗ Failed to reload script")

        def on_quit():
            self._cleanup()

        # Start keyboard monitoring
        # self._keyboard_monitor.start(on_reload, on_quit)

        try:
            logger.info("Blender is running. Keyboard shortcuts:")
            logger.info("  r - Reload project")
            logger.info("  q - Quit session")

            # Wait for Blender process to end
            process.wait()
            logger.info(
                f"Blender process has ended (pid: {process.pid})")

        except KeyboardInterrupt:
            logger.info("Stopping monitoring...")

        finally:
            self._cleanup()

    def _cleanup(self):
        """Clean up all monitoring and processes."""
        self._keyboard_monitor.stop()
        self._output_monitor.stop()
        self._subproc_manager.cleanup()


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
