import functools
import re
from pathlib import Path

import bpy

from anima.diagnostics import logger
from anima.utils.input import BlenderInputMonitor
from anima.utils.output import BlenderOutputMonitor
from anima.utils.project import get_blender_config, validate_project_configuration
from anima.utils.subprocess import SubprocessManager


class BlenderProcess:
    """Main facade class that coordinates all Blender operations."""

    def __init__(self):
        validate_project_configuration()
        self._subproc_manager = SubprocessManager()
        self._input_monitor = BlenderInputMonitor(self._subproc_manager)
        self._output_monitor = BlenderOutputMonitor(self._subproc_manager)

    def start(self) -> "BlenderProcess":
        """Start Blender and run the main.py script."""
        subproc_mgr = self._subproc_manager
        pid = subproc_mgr.subprocess.pid if subproc_mgr.subprocess else None
        try:
            if subproc_mgr.running():
                logger.info(f"Found running Blender instance (pid: {pid})")
            else:
                logger.info("Starting Blender subprocess...")
                if not subproc_mgr.start():
                    raise RuntimeError("Failed to start Blender subprocess")
                self._input_monitor._configure_blender()

        except Exception as e:
            logger.error(f"Error running script: {e}")
            subproc_mgr.cleanup()
            raise
        return self

    def monitor(self) -> "BlenderProcess":
        """Monitor Blender with keyboard shortcuts."""
        subproc = self._subproc_manager.subprocess
        if not subproc:
            logger.error("No Blender process to monitor")
            return self

        # Start input/output monitoring
        self._input_monitor.start()
        self._output_monitor.start()

        try:
            # Wait for Blender process to end
            logger.info("Blender is running...")
            subproc.wait()
            logger.info("Blender process has ended")
        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt: Terminating Blender...")
        finally:
            self._input_monitor.stop()
            self._output_monitor.stop()
            self._subproc_manager.cleanup()
        return self

    def reload(self) -> "BlenderProcess":
        """Reload the main script in Blender."""
        self._input_monitor._reload_main()
        return self

    def quit(self):
        """Quit Blender gracefully."""
        self._input_monitor.quit_blender()


@functools.lru_cache(maxsize=1)
def get_blender_root_path() -> Path:
    """Get the root path of the Blender executable from pyproject.toml.
    Constructs the full path dynamically from install-dir and version.
    Returns:
        Path: The root path of the Blender executable.
    Raises:
        FileNotFoundError: If Blender path does not exist.
    """
    bl_config = get_blender_config()
    install_dir = bl_config.get("install-dir")
    version = bl_config.get("version")

    if not install_dir:
        raise ValueError("tool.blender.install-dir not found in pyproject.toml")
    if not version:
        raise ValueError("tool.blender.version not found in pyproject.toml")

    # Construct the full Blender directory path dynamically. Assumes the directory
    # follows the naming convention: blender-{version}-{platform}
    root_dir = Path(install_dir).expanduser() / f"blender-{version}-linux-x64"

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
    bl_path = get_blender_root_path() / "blender"
    if not bl_path.exists():
        raise FileNotFoundError(f"Blender path does not exist: {bl_path}")
    return bl_path


@functools.lru_cache(maxsize=1)
def blender_version(major_minor: bool = False) -> str:
    """Get the Blender version from pyproject.toml configuration.
    Args:
        major_minor (bool): If True, return only the major.minor version (e.g., "4.5").
    Returns:
        str: The Blender version (e.g., "4.5.1" or "4.5").
    """
    bl_config = get_blender_config()
    version = bl_config.get("version")
    if not version:
        raise ValueError("Blender version not found in pyproject.toml")
    elif major_minor:
        version = ".".join(version.split(".")[:2])
    return version


def configure_blender_viewport():
    """Configure the Blender 3D viewport to top view."""
    # Find and activate the 3D viewport
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                for region in area.regions:
                    if region.type == "WINDOW":
                        logger.debug("Found 3D viewport: overriding context")
                        override = {
                            "area": area,
                            "region": region,
                            "space_data": (area.spaces.active if hasattr(area.spaces, "active") else area.spaces[0]),
                        }
                        with bpy.context.temp_override(**override):
                            if bpy.ops.view3d.view_axis.poll():
                                bpy.ops.view3d.view_axis(type="TOP")
                                logger.debug("Set 3D viewport to top view")
                        break
                break
        else:
            continue
        break
