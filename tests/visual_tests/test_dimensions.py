"""Integration checks using the installed TeX toolchain and real glyph outlines."""

import pytest

from anima.latex.glyph_group import GlyphGroup
from anima.latex.tex_doc_processor import TeXDocumentProcessor
from anima.latex.tex_document import TeXDocument
from anima.scene.profile import FRAME_16X9_V1


@pytest.mark.parametrize("font_size", [7.5, 15])
def test_real_tex_text_math_and_fraction_match_native_sizing(font_size):
    text = r"H $x^2+\frac{a}{b}$"
    group = GlyphGroup.from_tex_string(text, font_size=font_size)
    document = (
        TeXDocument()
        .set_defaults()
        .add_to_body(rf"{{\fontsize{{{font_size}}}{{{font_size * 1.2}}}\selectfont {text}}}")
    )
    factor = FRAME_16X9_V1.tex_point_size / (72 / 72.27)

    with TeXDocumentProcessor(document) as (paths, positions):
        assert len(group) == len(positions)
        assert any(label == "rule" for _, _, _, label in positions)
        for glyph, (glyph_id, (x, y), _, _) in zip(group, positions):
            x_min, x_max, y_min, y_max = paths[glyph_id].bbox()
            assert tuple(glyph.location) == pytest.approx((x * factor, y * factor, 0), abs=1e-6)
            assert (glyph.bbox.x_min, glyph.bbox.x_max) == pytest.approx((x_min * factor, x_max * factor), abs=1e-6)
            assert (glyph.bbox.y_min, glyph.bbox.y_max) == pytest.approx((-y_min * factor, -y_max * factor), abs=1e-6)


def test_real_tex_font_size_and_inline_override():
    small = GlyphGroup.from_tex_string(r"H $x^2+\frac{a}{b}$", font_size=7.5)
    large = GlyphGroup.from_tex_string(r"H $x^2+\frac{a}{b}$", font_size=15)
    assert large[0].bbox.y_min - large[0].bbox.y_max > 1.8 * (small[0].bbox.y_min - small[0].bbox.y_max)
    assert large[1].bbox.y_min - large[1].bbox.y_max > 1.5 * (small[1].bbox.y_min - small[1].bbox.y_max)

    text = r"{\fontsize{12}{14.4}\selectfont H $x^2$}"
    override_small = GlyphGroup.from_tex_string(text, font_size=7.5)
    override_large = GlyphGroup.from_tex_string(text, font_size=15)
    assert len(override_small) == len(override_large)
    for first, second in zip(override_small, override_large):
        assert tuple(first.location) == pytest.approx(tuple(second.location), abs=1e-6)
        assert first.bbox == second.bbox
