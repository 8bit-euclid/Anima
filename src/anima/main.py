# fmt: off
# Add the project root and the src directory to the Python path
import sys
from dataclasses import replace
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
from anima.materials.material import create_raking_sun
from anima.materials.texture import TextureSet
from anima.primitives.polytopes import Rectangle
from anima.runtime import run_lesson
from anima.utils.render import RenderSettings, ensure_camera
from anima.utils.render_request import RenderRequest

# fmt: on

# Rendering is opt-in so that the normal interactive workflow is unchanged. Use `make render` (see the Makefile
# for the options); it renders PNG frames headlessly (resumable after a crash or overheat), then encodes an MP4.
FINAL_RENDER = RenderSettings(engine="CYCLES", samples=256, resolution=(3840, 2160), denoise=True)
PREVIEW_RENDER = RenderSettings(engine="EEVEE", samples=16, resolution=(1920, 1080))
FRAME_RATE = 60


def get_render_config() -> tuple[RenderSettings | None, RenderRequest | None]:
    """Read the render options from the environment.

    Returns:
        The render settings and request, both None when rendering was not requested.
    """
    request = RenderRequest.from_env()
    if request is None:
        return None, None
    settings = replace(PREVIEW_RENDER if request.preview else FINAL_RENDER, device=request.device)
    return settings, request


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
    rect.set_textures(TextureSet.from_directory(TEXTURE_DIR, physical_size=10), bump_strength=0.5, bump_distance=0.1)

    test_bezier_splines(end_frame, color="red1", paper=rect)
    test_curve_joints(end_frame, color="yellow1", paper=rect)
    test_dashed_curves(end_frame, color="blue1", paper=rect)

    # A low sun circling once over the lesson, to show the paper relief. Add fill_energy=... to compare with a fixed fill.
    create_raking_sun(end_frame, elevation_deg=25, energy=4)

    # A rendered video needs a camera; frame the 20 x 10 paper top-down.
    if get_render_config()[0] is not None:
        ensure_camera(location=(0, 0, 10), orthographic_scale=20)

    # test_paper_textures()
    # render_gallery(output_dir="out", engines=("CYCLES", "EEVEE"))


if __name__ == "__main__":
    render_settings, render_request = get_render_config()
    run_lesson(
        build_scene,
        end_time="00:06",
        frame_rate=FRAME_RATE,
        use_default_lighting=False,
        render_settings=render_settings,
        render_request=render_request,
    )
