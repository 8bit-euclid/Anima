"""Render inward emboss profiles on a glyph and a polygon.

Run: uv run python -m tests.visual_tests.test_curve_emboss [output.png] [--width 0.18]
"""

import argparse
import random
import tempfile
from functools import partial
from pathlib import Path

import bpy
import svgpathtools as svgtools

from anima.globals.general import clear_scene
from anima.latex.glyph import Glyph
from anima.materials.material import create_color_material
from anima.materials.texture import TextureSet
from anima.primitives.chains import CurveLoop
from anima.primitives.curve_emboss import apply_emboss
from anima.primitives.group import Group
from anima.primitives.polytopes import Rectangle
from anima.utils.render import RenderSettings, configure_render, ensure_camera, render_still


def _label(text: str, position: tuple[float, float]) -> None:
    data = bpy.data.curves.new(f"{text}_label", type="FONT")
    data.body = text
    data.size = 0.18
    obj = bpy.data.objects.new(f"{text}_label", data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = (*position, 0.05)
    obj.visible_shadow = False
    data.materials.append(create_color_material("emboss_label", (0.03, 0.03, 0.03), emission_strength=1.0))


def _paper_height(path: Path) -> None:
    rng = random.Random(12)
    image = bpy.data.images.new("EmbossPaperHeight", width=128, height=128)
    image.colorspace_settings.name = "Non-Color"
    pixels = []
    for _ in range(128 * 128):
        value = rng.uniform(0.35, 0.65)
        pixels.extend((value, value, value, 1))
    image.pixels = pixels
    image.filepath_raw = str(path)
    image.file_format = "PNG"
    image.save()
    bpy.data.images.remove(image)


def _profile(t: float, depth: float) -> float:
    return depth * t * t * (3 - 2 * t)


def build_emboss_scene(textures: TextureSet, *, width: float = 0.18) -> None:
    """Build textured embossed shapes with and without round joints."""
    color = (0.70, 0.60, 0.46)
    paper = Rectangle(8.8, 9.5, name="EmbossPaper")
    paper.set_color(color)
    paper.set_textures(textures, bump_strength=0.35, bump_distance=0.025)
    paper.layer = -1

    outline = svgtools.parse_path("M 0,0 L 1,-2.8 L 2,0 Z M 0.7,-0.8 L 1.3,-0.8 L 1,-1.8 Z").reversed()
    polygon_outline = svgtools.parse_path("M -0.85,-0.85 L 0.85,-0.85 L 0.85,0.85 L -0.85,0.85 Z").reversed()
    for joints, y in ((False, 2.15), (True, -2.15)):
        _label(f"{'Round joints' if joints else 'No joints'}  |  width {width:g}", (-3.8, y + 2.05))
        for label, x, depth in (("Recessed glyph", -3.8, -0.06), ("Raised glyph", -1.0, 0.06)):
            glyph = Glyph(outline, name=label, with_border=not joints)
            if joints:
                boundaries = [
                    CurveLoop.from_svg_path(subpath, create_joints=True, name=f"{label}_boundary")
                    for subpath in outline.continuous_subpaths()
                ]
                for boundary in boundaries:
                    glyph.add_child(boundary)
            else:
                boundaries = glyph.border.subpaths
            glyph.location = (x, y - 1.1, 0)
            glyph.set_color(color)
            glyph.set_textures(textures, bump_strength=0.35, bump_distance=0.025)
            glyph.body.object.visible_shadow = False
            for boundary in boundaries:
                apply_emboss(boundary, width=width, height=partial(_profile, depth=depth))
                boundary.layer = 1
            _label(label, (x, y - 1.6))

        polygon = Rectangle(1.7, 1.7, name="EmbossPolygon")
        boundary = CurveLoop.from_svg_path(polygon_outline, create_joints=joints, name="EmbossPolygonBoundary")
        group = Group([polygon, boundary], name="EmbossPolygonGroup")
        group.location = (2.4, y, 0)
        group.set_color(color)
        group.set_textures(textures, bump_strength=0.35, bump_distance=0.025)
        polygon.object.visible_shadow = False
        apply_emboss(boundary, width=width, height=lambda t: _profile(t, -0.06))
        boundary.layer = 1
        _label("Recessed polygon", (1.55, y - 1.6))
    _label("Bump shading only: no displaced geometry", (-3.8, -4.25))

    light = bpy.data.objects.new("EmbossSun", bpy.data.lights.new("EmbossSun", "SUN"))
    bpy.context.scene.collection.objects.link(light)
    light.rotation_euler = (0.65, -0.8, -0.25)
    light.data.energy = 3.0
    ensure_camera(location=(0, 0, 10), orthographic_scale=9.0)


def render_emboss_gallery(path: str | Path, *, width: float = 0.18) -> Path:
    """Render the textured emboss gallery with Cycles on the GPU.

    Args:
        path: Destination render path.
        width: Inward emboss band width in local units.

    Returns:
        The rendered image path.

    Raises:
        RuntimeError: If no supported Cycles GPU is available.
    """
    clear_scene()
    with tempfile.TemporaryDirectory(prefix="anima_emboss_") as directory:
        height_path = Path(directory) / "height.png"
        _paper_height(height_path)
        build_emboss_scene(TextureSet(height=height_path, physical_size=(2.0, 2.0)), width=width)
        configure_render(
            RenderSettings(engine="CYCLES", device="GPU", samples=128, resolution=(1200, 1400), denoise=False)
        )
        return render_still(path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", nargs="?", type=Path, default=Path("out/curve_emboss.png"))
    parser.add_argument("--width", type=float, default=0.18, help="inward emboss band width in local units")
    args = parser.parse_args()
    print(f"Rendered {render_emboss_gallery(args.output, width=args.width)}")
