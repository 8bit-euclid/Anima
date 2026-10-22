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
from tests.visual_tests.test_curves import test_bezier_splines, test_curve_joints, test_dashed_curves
from tests.visual_tests.test_latex import test_text_to_glyphs
from tests.visual_tests.test_textures import TEXTURE_DIR, render_gallery, test_paper_textures

from anima.globals.general import to_frame
from anima.materials.texture import TextureSet
from anima.primitives.polytopes import Rectangle
from anima.runtime import run_lesson

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
    # test_text_to_glyphs()
    end_frame = to_frame(end_time)

    rect = Rectangle(length=20, width=10)
    rect.layer = -1
    rect.set_palette_color("byrne_euclid", "paper")
    rect.set_textures(TextureSet.from_directory(TEXTURE_DIR, physical_size=10))

    test_bezier_splines(end_frame, color="red1", paper=rect)
    test_curve_joints(end_frame, color="yellow1", paper=rect)
    test_dashed_curves(end_frame, color="blue1", paper=rect)

    # test_paper_textures()
    # render_gallery(output_dir="out", engines=("CYCLES", "EEVEE"))


if __name__ == "__main__":
    run_lesson(build_scene, end_time="00:06")
