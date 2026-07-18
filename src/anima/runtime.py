"""Reusable Blender bootstrap for Anima lesson scripts.

Lesson scripts should call `run_lesson(build_scene, end_frame=...)` from their
`if __name__ == "__main__":` block instead of re-implementing scene setup.
"""

from collections.abc import Callable

import bpy

from anima.diagnostics import logger
from anima.globals.general import clear_scene, deselect_all, ebpy, hide_relationship_lines, to_frame
from anima.utils.blender import configure_blender_panes, configure_blender_viewport, frame_scene_in_viewport
from anima.utils.socket.server import BlenderSocketServer


def run_lesson(
    build_scene: Callable[[str, str], None],
    start_time: str = "00:00",
    end_time: str | None = None,
    frame_rate: int = 60,
):
    """Bootstrap Blender, build a lesson's scene, then start playback.

    Args:
        build_scene (Callable[[int], None]): Callable that populates the scene and returns the end frame.
        start_time (str): The time at which the lesson's animation starts.
        end_time (str): The time at which the lesson's animation ends.
        frame_rate (int): Render frame rate.
        zoom_delta (float): Extra viewport zoom steps applied after framing the scene.
    """
    logger.info("Running lesson script in Blender")

    BlenderSocketServer().start()

    configure_blender_viewport()
    configure_blender_panes()

    clear_scene()
    ebpy.set_render_fps(frame_rate)

    logger.info("Building scene...")
    build_scene(start_time, end_time)

    hide_relationship_lines()
    deselect_all()

    # Set start and end frames
    start_frame = to_frame(start_time)
    end_frame = to_frame(end_time)
    ebpy.set_start_frame(start_frame)
    ebpy.set_end_frame(end_frame + 50)

    # Preset viewpoint
    bpy.context.preferences.view.show_splash = False

    # Stop any running animations first (when reloading)
    bpy.ops.screen.animation_cancel(restore_frame=False)

    # Reset to frame one, frame the scene, zoom in, and play
    bpy.context.scene.frame_current = 1
    frame_scene_in_viewport(zoom_delta=2.5)
    bpy.ops.screen.animation_play()
