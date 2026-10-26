"""Visual tests for PBR paper textures.

In Blender (see `anima.main`), call `test_paper_textures` from the scene builder, then open the Shading workspace
and select the paper or a curve to inspect its `anima_tex_*` nodes. Headless, run this module to render a gallery
of variants with both engines:

    uv run python -m tests.visual_tests.test_textures [output_dir]
"""

import os
import sys
from pathlib import Path

import bpy

from anima.globals.general import clear_scene
from anima.materials.texture import TextureSet
from anima.primitives.bezier_spline import BezierSpline
from anima.primitives.polytopes import Rectangle
from anima.utils.blender import set_viewport_shading
from anima.utils.render import RenderSettings, configure_render, ensure_camera, render_still

TEXTURE_DIR = Path(os.environ.get("ANIMA_TEXTURE_DIR", "~/Downloads/Other_Paper_vmcmfh1n_8K_surface_ms")).expanduser()
PAPER_SIZE_UNITS = 2.5  # Scene units covered by one tile of the texture pack.

CURVE_COLORS = ("red1", "blue1", "yellow1")


def test_paper_textures(
    end_frame: int = 0,
    albedo_mode: str = "modulate",
    bump_strength: float = 0.2,
    texture_dir: Path = TEXTURE_DIR,
) -> tuple[Rectangle, list[BezierSpline]]:
    """Build a textured paper sheet with coloured curves that inherit its textures.

    Args:
        end_frame: Unused; accepted for consistency with the other visual tests.
        albedo_mode: How curves treat the paper albedo: "modulate", "multiply", "ignore" or "replace".
        bump_strength: Strength of the height-map bump.
        texture_dir: Folder holding the texture pack.

    Returns:
        The paper and the curves.
    """
    textures = TextureSet.from_directory(texture_dir, physical_size=PAPER_SIZE_UNITS)

    paper = Rectangle(6, 4, name="Paper")
    paper.set_palette_color("byrne_euclid", "paper")
    paper.set_textures(textures, bump_strength=bump_strength)

    curves = []
    for i, color in enumerate(CURVE_COLORS):
        y = (1 - i) * 0.5
        curve = BezierSpline([(-1.4, y), (0, y + 0.25), (1.4, y)], name=f"Curve_{color}")
        curve.set_width(0.1)
        curve.layer = 1  # Sit above the paper to avoid z-fighting.
        curve.set_palette_color("byrne_euclid", color)
        curve.inherit_textures_from(paper, albedo_mode=albedo_mode)
        curves.append(curve)

    _ensure_raking_light()
    set_viewport_shading("MATERIAL")
    return paper, curves


def _ensure_raking_light() -> None:
    """Tilt the scene's sun (adding one if needed) so the paper relief catches light."""
    sun = next((o for o in bpy.data.objects if o.type == "LIGHT" and o.data.type == "SUN"), None)
    if sun is None:
        sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
        bpy.context.scene.collection.objects.link(sun)
    sun.rotation_euler = (0.9, 0.3, 0.5)
    sun.data.energy = 4


# Name -> keyword arguments for test_paper_textures.
VARIANTS: dict[str, dict] = {
    "modulate": {"albedo_mode": "modulate"},
    "multiply": {"albedo_mode": "multiply"},
    "ignore": {"albedo_mode": "ignore"},
}


def render_gallery(output_dir: str | Path, engines: tuple[str, ...] = ("CYCLES", "EEVEE")) -> list[Path]:
    """Render every variant with every engine to `<output_dir>/<variant>_<engine>.png`.

    Args:
        output_dir: Folder to write the images into.
        engines: The render engines to compare.

    Returns:
        The written image paths.
    """
    output_dir = Path(output_dir)
    written = []
    for name, kwargs in VARIANTS.items():
        for engine in engines:
            clear_scene()
            for mat in list(bpy.data.materials):
                bpy.data.materials.remove(mat)
            test_paper_textures(**kwargs)
            bpy.context.scene.camera = None
            camera = ensure_camera(location=(0, 0, 10), orthographic_scale=2.4)
            camera.data.ortho_scale = 2.4
            configure_render(RenderSettings(engine=engine, samples=32, resolution=(960, 640)))
            written.append(render_still(output_dir / f"{name}_{engine.lower()}.png"))
    return written


if __name__ == "__main__":
    for path in render_gallery(sys.argv[1] if len(sys.argv) > 1 else "/tmp/anima_textures"):
        print("Rendered", path)
