"""Reference scene for checking the paper profile at the intended delivery size.

Render a single frame from the repository root:

    make render-frame SCRIPT=scripts/calibrate_dimensions.py FRAME=1

This defaults to a 4K (3840x2160) Cycles render. For a 1080p EEVEE preview:

    make render-frame SCRIPT=scripts/calibrate_dimensions.py FRAME=1 PREVIEW=1

Add DEVICE=CPU to use the CPU for Cycles, or DEPTH=16 for 16-bit PNG frames.
To render the full scene to an MP4, use `make render` with the same SCRIPT
and settings, for example:

    make render SCRIPT=scripts/calibrate_dimensions.py OUTPUT=out/dimensions.mp4
"""

from anima.latex.glyph_group import GlyphGroup
from anima.primitives.curves import DEFAULT_LINE_WIDTH, THICK_LINE_WIDTH, THIN_LINE_WIDTH
from anima.primitives.lines import Segment
from anima.primitives.points import Point
from anima.runtime import run_lesson
from anima.scene.background import DEFAULT_BACKGROUND_TEXTURE_DIR, create_background
from anima.scene.render_config import get_render_config
from anima.scene.setup import configure_camera, configure_lighting
from anima.scene.state import get_profile


def build_scene(start_time: str, end_time: str) -> None:
    """Build a static reference scene with safe bounds, text, math, and strokes."""
    profile = get_profile()
    background = create_background(DEFAULT_BACKGROUND_TEXTURE_DIR)
    configure_lighting()
    configure_camera()

    safe_x, safe_y = (size / 2 for size in profile.safe_size)
    corners = ((-safe_x, -safe_y), (safe_x, -safe_y), (safe_x, safe_y), (-safe_x, safe_y))
    for start, end in zip(corners, corners[1:] + corners[:1]):
        guide = Segment(start, end, width=THIN_LINE_WIDTH)
        guide.set_palette_color("byrne_euclid", "red1")

    # Layout is expressed in profile units so it follows any frame or typography change.
    body_size = profile.body_font_size * profile.tex_point_size
    label_size = profile.label_font_size * profile.tex_point_size
    title_size = profile.title_font_size * profile.tex_point_size
    left = -safe_x + 1.5 * body_size
    y = safe_y - 1.3 * title_size
    samples = (
        ("Dimensions", profile.title_font_size),
        ("Body text: AaBb 012", profile.body_font_size),
        (r"$E = mc^2 \qquad \frac{x^2-1}{x^2+1}$", profile.body_font_size),
        (r"$\sum_{i=1}^{n} x_i \qquad \int_0^1 f(x)\,dx$", profile.body_font_size),
        ("Small label: Aa 012", profile.label_font_size),
    )
    for index, (text, font_size) in enumerate(samples):
        if index:
            y -= 2 * font_size * profile.tex_point_size
        group = GlyphGroup.from_tex_string(text, font_size=font_size)
        group.location = (left, y, 0)
        group.set_palette_color("byrne_euclid", "black")
        group.inherit_textures_from(background)

    stroke_length = 5 * label_size
    stroke_pitch = 0.5 * label_size
    stroke_top = y - 1.5 * body_size
    for row, width in enumerate((THIN_LINE_WIDTH, DEFAULT_LINE_WIDTH, THICK_LINE_WIDTH)):
        stroke_y = stroke_top - row * stroke_pitch
        line = Segment((left, stroke_y), (left + stroke_length, stroke_y), width=width)
        line.set_palette_color("byrne_euclid", "blue1")
        line.inherit_textures_from(background)

    dot_radius = label_size / 4
    dot_y = stroke_top - stroke_pitch
    for index, color in enumerate(("red1", "blue1", "yellow1")):
        dot_x = left + stroke_length + 1.5 * body_size + index * 5 * dot_radius
        point = Point(location=(dot_x, dot_y), radius=dot_radius)
        point.set_palette_color("byrne_euclid", color)
        point.inherit_textures_from(background)


if __name__ == "__main__":
    render_settings, render_request = get_render_config()
    run_lesson(
        build_scene,
        end_time="00:02",
        use_default_lighting=False,
        render_settings=render_settings,
        render_request=render_request,
    )
