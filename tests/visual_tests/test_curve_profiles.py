"""Render width-profile examples with Cycles on the GPU.

Run: uv run python -m tests.visual_tests.test_curve_profiles [output.png]
"""

import math
import sys
from pathlib import Path

import bpy

from anima.globals.general import clear_scene
from anima.materials.material import create_color_material
from anima.primitives.bezier_spline import BezierSpline
from anima.primitives.chains import CurveChain
from anima.primitives.endcaps import RoundEndcap
from anima.primitives.lines import Segment
from anima.primitives.polytopes import Rectangle
from anima.utils.render import RenderSettings, configure_render, ensure_camera, render_still


def _label(text: str, position: tuple[float, float]) -> None:
    data = bpy.data.curves.new(f"{text}_label", type="FONT")
    data.body = text
    data.size = 0.16
    obj = bpy.data.objects.new(f"{text}_label", data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = (*position, 0.05)
    obj.visible_shadow = False
    data.materials.append(create_color_material("profile_label", (0.03, 0.03, 0.03), emission_strength=1.0))


def build_curve_profile_scene() -> None:
    """Add a gallery of opacity, bump, joint, and dashed profiles to the scene."""
    paper = Rectangle(6.6, 4.7, name="ProfilePaper")
    paper.set_color((0.82, 0.78, 0.70))
    paper.layer = -1  # Keep the paper below the strokes without visible cast-shadow offsets.

    opacity = Segment((-2.5, 1.55), (2.5, 1.55), width=0.42, name="OpacityProfile")
    opacity.set_color((0.5, 0.025, 0.02))
    opacity.set_width_profile(opacity=lambda u: u * u * (3 - 2 * u))
    _label("Opacity: 0 (top) to 1 (bottom)", (-2.5, 1.13))

    relief = BezierSpline([(-2.5, 0.25), (0, 0.45), (2.5, 0.25)], width=0.42, name="BumpProfile")
    relief.set_color((0.025, 0.10, 0.42))
    relief.set_width_profile(height=lambda u: 0.065 * math.sin(math.pi * u))
    _label("Bump: raised middle, no geometry displacement", (-2.5, -0.13))

    chain = CurveChain(
        [Segment((-2.5, -1.6), (-1.6, -1.6)), Segment((-1.6, -1.6), (-0.8, -0.9))],
        width=0.30,
        name="ProfileJoint",
    )
    chain.curves[0].attachment_0 = RoundEndcap(width=0.30, radius=0.15)
    chain.set_color((0.05, 0.28, 0.08))
    chain.set_width_profile(height=lambda u: 0.035 * math.sin(math.pi * u), opacity=lambda u: 0.2 + 0.8 * u)
    _label("Combined: joint and cap", (-2.5, -2.05))

    base = Segment((0.2, -1.35), (2.5, -1.35), width=0.30, name="ProfileDashBase")
    base.set_color((0.23, 0.04, 0.26))
    base.set_width_profile(height=lambda u: 0.035 * math.sin(math.pi * u), opacity=lambda u: 0.2 + 0.8 * u)
    base.make_dashed(dash_len=0.45, gap_len=0.16)
    _label("Combined: dashes", (0.2, -2.05))

    light = bpy.data.objects.new("ProfileRakingSun", bpy.data.lights.new("ProfileRakingSun", "SUN"))
    bpy.context.scene.collection.objects.link(light)
    light.rotation_euler = (0.65, -0.8, -0.25)
    light.data.energy = 3.0
    camera = ensure_camera(location=(0, 0, 10), orthographic_scale=6.9)
    camera.location = (0, 0, 10)


def render_profile_gallery(path: str | Path) -> Path:
    """Clear the scene and render the profile gallery with Cycles on the GPU.

    Args:
        path: Destination render path.

    Returns:
        The path to the rendered image.

    Raises:
        RuntimeError: If no supported Cycles GPU is available.
    """
    clear_scene()
    build_curve_profile_scene()
    configure_render(RenderSettings(engine="CYCLES", device="GPU", samples=64, resolution=(1200, 900), denoise=False))
    return render_still(path)


if __name__ == "__main__":
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("out/curve_profiles.png")
    print(f"Rendered {render_profile_gallery(output)}")
