"""Reusable Blender bootstrap for Anima lesson scripts.

Lesson scripts should call `run_lesson(build_scene, end_frame=...)` from their
`if __name__ == "__main__":` block instead of re-implementing scene setup.
"""

from collections.abc import Callable

import bpy

from anima.diagnostics import logger
from anima.globals.general import clear_scene, deselect_all, ebpy, hide_relationship_lines, to_frame
from anima.utils.blender import (
    capture_viewport_state,
    configure_blender_panes,
    configure_blender_viewport,
    frame_scene_in_viewport,
    restore_viewport_state,
)
from anima.utils.render import RenderSettings, configure_render, render_frame, render_sequence
from anima.utils.render_request import RenderRequest
from anima.utils.socket.server import BlenderSocketServer

_INITIALIZED_KEY = "anima_lesson_initialized"


def run_lesson(
    build_scene: Callable[[str, str], None],
    start_time: str = "00:00",
    end_time: str | None = None,
    frame_rate: int = 60,
    use_default_lighting: bool = True,
    render_settings: RenderSettings | None = None,
    render_request: RenderRequest | None = None,
):
    """Bootstrap Blender, build a lesson's scene, then start playback (or render it, if requested).

    Args:
        build_scene (Callable[[int], None]): Callable that populates the scene and returns the end frame.
        start_time (str): The time at which the lesson's animation starts.
        end_time (str): The time at which the lesson's animation ends.
        frame_rate (int): Render frame rate.
        use_default_lighting (bool): Add a default sun light.
        render_settings (RenderSettings, optional): Render engine, samples and resolution to apply.
        render_request (RenderRequest, optional): If given (with `render_settings`), render the PNG frame
            sequence (or a single test frame) into the request's paths instead of starting viewport playback.
            Encoding to video is done separately by `anima.utils.encode`. When Blender runs headless
            (`bpy.app.background`), the socket server and all viewport/UI setup are skipped.
    """
    logger.info("Running lesson script in Blender")

    headless = bpy.app.background
    if not headless:
        BlenderSocketServer().start()

    # The driver namespace survives the module eviction done on reload. Its presence marks a reload.
    namespace = bpy.app.driver_namespace
    saved_view = capture_viewport_state() if namespace.get(_INITIALIZED_KEY) else None

    if not headless:
        if saved_view is None:
            configure_blender_viewport()
        configure_blender_panes()

    clear_scene()
    ebpy.set_render_fps(frame_rate)
    if render_settings is not None:
        configure_render(render_settings)

    # Set default lighting
    if use_default_lighting:
        bpy.ops.object.light_add(type="SUN")

    logger.info("Building scene...")
    build_scene(start_time, end_time)

    hide_relationship_lines()
    deselect_all()

    # Set start and end frames
    start_frame = to_frame(start_time)
    end_frame = to_frame(end_time)
    ebpy.set_start_frame(start_frame)
    ebpy.set_end_frame(end_frame + 50)

    if render_request is not None:
        _render(render_request, render_settings or RenderSettings())
        return
    if headless:
        return

    # Preset viewpoint
    bpy.context.preferences.view.show_splash = False

    # Stop any running animations first (when reloading)
    bpy.ops.screen.animation_cancel(restore_frame=False)

    # Reset to frame one, frame the scene, zoom in, and play animation
    bpy.context.scene.frame_current = 1
    if saved_view is None:
        frame_scene_in_viewport(zoom_delta=2.5)
    else:
        restore_viewport_state(saved_view)
    namespace[_INITIALIZED_KEY] = True
    bpy.ops.screen.animation_play()


def _render(request: RenderRequest, settings: RenderSettings) -> None:
    """Render a single test frame or the whole frame range, as described by `request`."""
    if request.frame is not None:
        logger.info(f"Rendering test frame {request.frame} to {request.still_path}")
        render_frame(request.still_path, request.frame, request.bit_depth)
        logger.info(f"Test frame written: {request.still_path}")
        return
    render_sequence(request.frames_dir, settings, request.bit_depth, request.restart, request.preview)
