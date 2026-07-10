import functools
from pathlib import Path

import bpy

from anima.diagnostics import logger
from anima.utils.input import BlenderInputMonitor
from anima.utils.output import BlenderOutputMonitor
from anima.utils.project import get_blender_config, validate_project_configuration
from anima.utils.subprocess import SubprocessManager

ZOOM_STEP_FACTOR = 1.2  # Each zoom step scales the view by roughly 20%


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
                # Focus the Blender window so keyboard shortcuts (e.g. spacebar to
                # pause) work immediately after starting Blender.
                try:
                    self._input_monitor._blender_to_front()
                except RuntimeError as e:
                    logger.warning(f"Could not focus Blender window: {e}")

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
def get_blender_python_path() -> Path:
    """Get the path to Blender's Python executable.

    Returns:
        Path: The path to Blender's Python executable.

    Raises:
        FileNotFoundError: If the Python executable path does not exist.
    """
    bl_path = get_blender_root_path()
    bl_version = blender_version(major_minor=True)
    python_path = bl_path / bl_version / "python" / "bin" / "python3.11"

    if not python_path.exists():
        raise FileNotFoundError(f"Blender Python executable does not exist: {python_path}")

    return python_path


@functools.lru_cache(maxsize=1)
def get_blender_site_packages_path() -> Path:
    """Get the site-packages path for Blender's Python installation.

    Returns:
        Path: The path to Blender's site-packages directory.

    Raises:
        FileNotFoundError: If the site-packages path does not exist.
    """
    bl_path = get_blender_root_path()
    bl_version = blender_version(major_minor=True)
    site_packages_path = bl_path / bl_version / "python" / "lib" / "python3.11" / "site-packages"

    if not site_packages_path.exists():
        raise FileNotFoundError(f"Blender site-packages path does not exist: {site_packages_path}")

    return site_packages_path


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


def _get_viewport_override() -> dict | None:
    """Find the 3D viewport and build a context override for it.
    Returns:
        dict | None: Context override for the 3D viewport, or None if no viewport was found.
    """
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                for region in area.regions:
                    if region.type == "WINDOW":
                        return {
                            "window": window,
                            "area": area,
                            "region": region,
                            "space_data": (area.spaces.active if hasattr(area.spaces, "active") else area.spaces[0]),
                        }
    return None


def configure_blender_viewport():
    """Configure the Blender 3D viewport to top view."""
    override = _get_viewport_override()
    if override is None:
        logger.warning("No 3D viewport found to configure")
        return

    logger.debug("Found 3D viewport: overriding context")
    with bpy.context.temp_override(**override):
        if bpy.ops.view3d.view_axis.poll():
            bpy.ops.view3d.view_axis(type="TOP")
            logger.debug("Set 3D viewport to top view")


def frame_scene_in_viewport(zoom_delta: float = 0):
    """Zoom the 3D viewport so that all visible scene objects fit in view.
    Args:
        zoom_delta (float): Extra zoom steps applied after framing. Negative zooms
            out, positive zooms in; each step scales the view by 20%. Applied by
            scaling the viewport's view distance directly, as the `view3d.zoom`
            operator only honours the sign of its delta when scripted.
    """
    override = _get_viewport_override()
    if override is None:
        logger.warning("No 3D viewport found to frame the scene")
        return

    # Apply the view change instantly; a pending smooth-view transition would
    # otherwise overwrite the zoom adjustment.
    prefs = bpy.context.preferences.view
    smooth_view = prefs.smooth_view
    prefs.smooth_view = 0
    try:
        with bpy.context.temp_override(**override):
            if bpy.ops.view3d.view_all.poll():
                bpy.ops.view3d.view_all(center=False)
                logger.debug("Framed all scene objects in the 3D viewport")
        if zoom_delta != 0:
            region_3d = override["space_data"].region_3d
            region_3d.view_distance *= ZOOM_STEP_FACTOR ** (-zoom_delta)
            logger.debug(f"Applied viewport zoom delta: {zoom_delta}")
    finally:
        prefs.smooth_view = smooth_view


def configure_blender_panes(sidebar_frac: float = 0.18, properties_height: int = 0):
    """Arrange the right-hand outliner/properties column.

    Moves area edges to reach an absolute target layout, so calling this repeatedly
    (e.g. on hot reload) is idempotent.

    Args:
        sidebar_frac (float): Target width of the outliner/properties column as a
            fraction of the total window width.
        properties_height (int): Target height of the properties editor in pixels.
            Values below Blender's minimum are clamped, collapsing the editor to
            just its header strip.

    Note:
        The layout is applied via a polling timer. `area_move` only passes its
        poll when the mouse cursor sits on an area edge (that is the only place
        an interactive edge drag can start), so each step warps the cursor onto
        the target edge and retries until Blender's event loop has registered
        the new cursor position.
    """
    state = {"step": 0, "retries": 40}

    def find_area(screen: bpy.types.Screen, area_type: str) -> bpy.types.Area | None:
        return next((a for a in screen.areas if a.type == area_type), None)

    def apply():
        window = bpy.context.window_manager.windows[0]
        screen = window.screen
        view3d = find_area(screen, "VIEW_3D")
        outliner = find_area(screen, "OUTLINER")
        props = find_area(screen, "PROPERTIES")
        if view3d is None or outliner is None or props is None:
            logger.warning("Viewport/outliner/properties areas not found; skipping pane layout")
            return None

        # Each step targets one area edge: the midpoint of the gutter between the
        # two adjacent areas, and the delta needed to reach the target layout.
        if state["step"] == 0:
            # Vertical edge between the viewport and the sidebar. A negative delta
            # moves it left, widening the sidebar.
            edge_x = (view3d.x + view3d.width + outliner.x) // 2
            edge_y = outliner.y + outliner.height // 2
            delta = outliner.width - int(window.width * sidebar_frac)
        else:
            # Horizontal edge between the outliner and the properties editor.
            # A negative delta moves it down, shrinking the properties editor.
            edge_x = props.x + props.width // 2
            edge_y = (props.y + props.height + outliner.y) // 2
            delta = properties_height - props.height

        if delta:
            # The poll checks the real cursor position, so warp onto the edge. The
            # warp only takes effect once the event loop processes the mouse-move,
            # typically on the next timer tick.
            window.cursor_warp(edge_x, edge_y)
            with bpy.context.temp_override(window=window, screen=screen):
                if not bpy.ops.screen.area_move.poll():
                    state["retries"] -= 1
                    if state["retries"] <= 0:
                        logger.error("Failed to arrange panes: area_move never became available")
                        return None
                    return 0.05  # Retry shortly
                bpy.ops.screen.area_move(x=edge_x, y=edge_y, delta=delta)
                logger.debug(f"Pane layout step {state['step']}: moved edge by {delta}px")

        state["step"] += 1
        if state["step"] < 2:
            return 0.0  # Proceed to the next edge

        # Done: park the cursor in the viewport so that shortcuts (e.g. space to
        # pause) land there immediately.
        window.cursor_warp(view3d.x + view3d.width // 2, view3d.y + view3d.height // 2)
        return None

    bpy.app.timers.register(apply, first_interval=0.0)
