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
from tests.visual_tests.test_curves import (
    test_bezier_splines,
    test_curve_joints,
    test_curve_loop,
    test_dashed_curves,
)
from tests.visual_tests.test_latex import test_text_to_glyphs
from tests.visual_tests.test_reveals import test_curves_reveal, test_latex_write_on
from tests.visual_tests.test_textures import render_gallery, test_paper_textures

from anima.animation.scheduler import Scheduler
from anima.animation.timeline import as_timedelta, to_frame
from anima.materials.material import create_raking_sun
from anima.runtime import run_lesson
from anima.scene.background import DEFAULT_BACKGROUND_TEXTURE_DIR, create_background
from anima.scene.render_config import get_render_config
from anima.scene.setup import configure_camera, configure_lighting

# fmt: on


def build_scene(start_time: str, end_time: str):
    """Build the default demo scene. Used when `ANIMA_SCRIPT` is not set.

    See `anima.runtime.run_lesson` for the shared bootstrap this relies on, and
    duplicate `<course>/lessons/_lesson_template.py` (in the sibling Courses/
    repo, not tracked here) to author actual lesson content instead of editing
    this file.

    Args:
        start_time (str): The time at which the lesson's animation starts.
        end_time (str): The time at which the lesson's animation ends.
    """
    duration = as_timedelta(end_time) - as_timedelta(start_time)

    create_background(DEFAULT_BACKGROUND_TEXTURE_DIR)
    configure_lighting()

    half = duration / 2
    test_bezier_splines(half, color="red1")
    test_curve_joints(half, color="yellow1")
    test_curve_loop(half, color="blue1")
    test_dashed_curves(half, color="blue1")
    test_curves_reveal(half)
    test_text_to_glyphs()
    test_latex_write_on(half)

    # To use create_raking_sun instead, remove the fixed sun created by configure_lighting first.

    configure_camera()

    # test_paper_textures()
    # render_gallery(output_dir="out", engines=("CYCLES", "EEVEE"))


if __name__ == "__main__":
    render_settings, render_request = get_render_config()
    run_lesson(
        build_scene,
        end_time="00:10",
        use_default_lighting=False,
        render_settings=render_settings,
        render_request=render_request,
    )
