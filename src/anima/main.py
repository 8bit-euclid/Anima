# fmt: off
# Add the project root and the src directory to the Python path
import sys
from pathlib import Path

pkg_dir = Path(__file__).parent  # src/anima/
src_dir = pkg_dir.parent         # src/
proj_root = src_dir.parent       # project root

paths_to_add = [str(proj_root), str(src_dir)]
for path in paths_to_add:
    if path not in sys.path:
        sys.path.insert(0, path)

# Now import modules as usual
import bpy

from anima.diagnostics import logger
from anima.globals.general import (
    clear_scene,
    deselect_all,
    ebpy,
    hide_relationship_lines,
    to_frame,
)
from anima.utils.blender import configure_blender_viewport
from anima.utils.socket.server import BlenderSocketServer
from tests.visual_tests.test_curves import (
    test_bezier_splines,
    test_curve_joints,
    test_dashed_curves,
)
from tests.visual_tests.test_latex import test_text_to_glyphs

# fmt: on


def main():
    logger.info("Running main script in Blender")

    BlenderSocketServer().start()

    configure_blender_viewport()

    clear_scene()
    ebpy.set_render_fps(60)

    end_frame = to_frame("00:06")

    # Run visual tests
    logger.info("Running visual tests...")
    # test_text_to_glyphs()
    test_bezier_splines(end_frame)
    test_curve_joints(end_frame)
    test_dashed_curves(end_frame)

    hide_relationship_lines()
    deselect_all()

    # Set end frame
    ebpy.set_end_frame(end_frame + 50)

    # Preset viewpoint
    bpy.context.preferences.view.show_splash = False

    # Stop any running animations first (when reloading)
    bpy.ops.screen.animation_cancel(restore_frame=False)

    # Reset to frame one and play
    bpy.context.scene.frame_current = 1
    bpy.ops.screen.animation_play()


if __name__ == "__main__":
    main()
