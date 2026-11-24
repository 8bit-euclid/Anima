"""Render approximate curve-boundary bleed on a glyph and a polygon.

Run: uv run python -m tests.visual_tests.test_curve_bleed [output.png]
"""

import sys
from pathlib import Path

import bpy
import svgpathtools as svgtools

from anima.globals.general import clear_scene
from anima.latex.glyph import Glyph
from anima.materials.material import create_color_material
from anima.primitives.chains import CurveLoop
from anima.primitives.curve_bleed import apply_bleed
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
    data.materials.append(create_color_material("bleed_label", (0.03, 0.03, 0.03), emission_strength=1.0))


def build_bleed_scene() -> None:
    """Build a before-and-after glyph and an independently defined polygon."""
    paper = Rectangle(8.8, 4.5, name="BleedPaper")
    paper.set_color((0.82, 0.78, 0.70))
    paper.layer = -2
    outline = svgtools.parse_path("M 0,0 L 1,-2.8 L 2,0 Z M 0.7,-0.8 L 1.3,-0.8 L 1,-1.8 Z").reversed()
    for name, x, with_bleed in (("Original", -3.8, False), ("Bleeding", -1.0, True)):
        glyph = Glyph(outline, name=name, with_border=True)
        glyph.location = (x, -1.1, 0)
        glyph.set_color((0.36, 0.025, 0.02))
        if with_bleed:
            for boundary in glyph.border.subpaths:
                apply_bleed(boundary, width=0.216)
                boundary.layer = -1
        _label(name, (x, -1.6))

    polygon = Rectangle(1.7, 1.7, name="BleedPolygon")
    outline = svgtools.parse_path("M -0.85,-0.85 L 0.85,-0.85 L 0.85,0.85 L -0.85,0.85 Z").reversed()
    boundary = CurveLoop.from_svg_path(outline, name="PolygonBoundary")
    group = Group([polygon, boundary], name="PolygonWithBoundary")
    group.location = (2.4, 0.0, 0)
    group.set_color((0.03, 0.09, 0.36))
    apply_bleed(boundary, width=0.216)
    boundary.layer = -1
    _label("Polygon bleed", (1.55, -1.6))
    _label("Approximate bands: corners can have gaps or overlaps", (-3.8, -2.0))

    light = bpy.data.objects.new("BleedSun", bpy.data.lights.new("BleedSun", "SUN"))
    bpy.context.scene.collection.objects.link(light)
    light.rotation_euler = (0.65, -0.8, -0.25)
    light.data.energy = 3.0
    ensure_camera(location=(0, 0, 10), orthographic_scale=9.0)


def render_bleed_gallery(path: str | Path) -> Path:
    """Render the bleed comparison with Cycles on the GPU.

    Args:
        path: Destination render path.

    Returns:
        The rendered image path.

    Raises:
        RuntimeError: If no supported Cycles GPU is available.
    """
    clear_scene()
    build_bleed_scene()
    configure_render(RenderSettings(engine="CYCLES", device="GPU", samples=64, resolution=(1200, 700), denoise=False))
    return render_still(path)


if __name__ == "__main__":
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("out/curve_bleed.png")
    print(f"Rendered {render_bleed_gallery(output)}")
