"""Render a Cycles comparison of black ink treatments on the demo paper.

Run in a fresh Blender Python process:

    uv run python -m tests.visual_tests.test_black_ink OUTPUT_DIR

The paper maps come from ``ANIMA_TEXTURE_DIR`` or the default background directory.
Each treatment uses the same scene positions, light, texture maps and sample count.
These deliberately exaggerated variants make the differences easier to see.
The height masks reveal the actual paper behind the glyphs through the public
texture API; they do not modify Anima's material defaults.
"""

import sys
from pathlib import Path

import bpy

from anima.globals.general import clear_scene
from anima.latex.glyph_body import MeshQuality
from anima.latex.glyph_group import GlyphGroup
from anima.scene.background import DEFAULT_BACKGROUND_TEXTURE_DIR, create_background
from anima.scene.setup import configure_camera, configure_lighting
from anima.utils.render import RenderSettings, configure_render, render_still


def render_comparison(output_dir: str | Path) -> list[Path]:
    """Render five exaggerated material variants at normal size and close up.

    Args:
        output_dir: Directory for the ten PNG renders.

    Returns:
        Paths to the rendered images.
    """
    clear_scene()
    background = create_background(DEFAULT_BACKGROUND_TEXTURE_DIR)
    configure_lighting()
    configure_render(
        RenderSettings(
            engine="CYCLES",
            samples=64,
            resolution=(1920, 1080),
            device="GPU",
            denoise=True,
            denoiser="OPENIMAGEDENOISE",
        )
    )
    scene = bpy.context.scene
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 4
    camera = configure_camera()

    title = GlyphGroup.from_tex_string("Anima 012: AaBbOo", name="BlackInk", mesh_quality=MeshQuality.high())
    title.location = (-8.5, 4.0, 0)
    title.set_palette_color("byrne_euclid", "black")
    title.inherit_textures_from(background, mottling_strength=0.5)

    radical = GlyphGroup.from_tex_string(r"$\sqrt{x^2+y^2}$", name="RedRadical", mesh_quality=MeshQuality.high())
    radical.location = (-8.5, 2.2, 0)
    radical.set_palette_color("byrne_euclid", "red1")
    radical.inherit_textures_from(background, mottling_strength=0.5)

    h1 = 0.05
    h2 = 0.1
    # h1 = 0.25
    # h2 = 0.75
    v1 = 0.2
    variants = (
        # ("01_black_matte", 0.0, None, (0.0, 1.0)),
        # ("02_black_specular", 0.25, None, (0.0, 1.0)),
        ("03_height_gradient", 0.0, (h1, h2), (v1, 1.0)),
        # ("04_height_step", 0.0, (h1, h1), (0.0, 1.0)),
        ("05_height_specular", 0.25, (h1, h2), (v1, 1.0)),
    )
    output_dir = Path(output_dir)
    paths = []
    for name, specular, reveal, coverage in variants:
        title.set_material_properties(specular_ior_level=specular)
        title.inherit_textures_from(background, mottling_strength=0.5, height_reveal=reveal, ink_coverage=coverage)
        for view, location, scale, crop in (
            # ("normal", (0, 0, 10), 20.0, True),
            ("detail", (-8.0, 4.17, 10), 1.05, False),
        ):
            camera.location = location
            camera.data.ortho_scale = scale
            scene.render.use_border = crop
            scene.render.use_crop_to_border = crop
            if crop:
                scene.render.border_min_x = 100 / 1920
                scene.render.border_max_x = 690 / 1920
                scene.render.border_min_y = 1 - 410 / 1080
                scene.render.border_max_y = 1 - 85 / 1080
            paths.append(render_still(output_dir / f"{name}_{view}.png"))
    return paths


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: uv run python -m tests.visual_tests.test_black_ink OUTPUT_DIR")
    for path in render_comparison(sys.argv[1]):
        print(f"Rendered {path}", flush=True)
