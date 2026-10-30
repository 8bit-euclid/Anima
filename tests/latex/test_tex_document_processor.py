from anima.latex.tex_document import TeXDocument
from anima.latex.tex_document_processor import TeXDocumentProcessor, _extract_text_glyphs


def test_extract_text_glyph_names_for_private_use_characters(tmp_path):
    svg_file = tmp_path / "text.svg"
    svg_file.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg">
        <defs>
            <font id="mathfont">
                <font-face font-family="mathfont"/>
                <glyph unicode="&#xe050;" glyph-name="summationtext"/>
                <glyph unicode="x" glyph-name="x"/>
            </font>
        </defs>
        <style><![CDATA[text.f0 {font-family:mathfont;font-size:10px}]]></style>
        <text class="f0">A <tspan>B</tspan> Ω &#xe050;x</text>
        </svg>""",
        encoding="utf-8",
    )

    assert _extract_text_glyphs(svg_file) == [
        ("A", None),
        ("B", None),
        ("Ω", None),
        ("\ue050", "summationtext"),
        ("x", None),
    ]


def test_extract_text_glyph_names_use_the_text_font_family(tmp_path):
    svg_file = tmp_path / "text.svg"
    svg_file.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg">
        <defs>
            <font id="font-a">
                <font-face font-family="font-a"/>
                <glyph unicode="&#xe000;" glyph-name="left-from-font-a"/>
            </font>
            <font id="font-b">
                <font-face font-family="font-b"/>
                <glyph unicode="&#xe000;" glyph-name="left-from-font-b"/>
            </font>
        </defs>
        <style><![CDATA[
            text.f0 {font-family:font-a;font-size:10px}
            text.f1 {font-family:font-b;font-size:10px}
        ]]></style>
        <text class="f0">&#xe000;</text>
        <text class="f1">&#xe000;</text>
        </svg>""",
        encoding="utf-8",
    )

    assert _extract_text_glyphs(svg_file) == [
        ("\ue000", "left-from-font-a"),
        ("\ue000", "left-from-font-b"),
    ]


def test_extract_glyph_data_includes_fraction_rule_in_svg_order(tmp_path):
    svg_file = tmp_path / "doc.svg"
    svg_file.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg"
             xmlns:xlink="http://www.w3.org/1999/xlink">
        <defs>
            <path id="g0-49" d="M0 0 L1 0 L1 1 L0 1 Z"/>
            <path id="g0-50" d="M0 0 L1 0 L1 1 L0 1 Z"/>
        </defs>
        <g id="page1">
            <use x="0" y="0" xlink:href="#g0-49"/>
            <rect x="1" y="1" width="2" height=".1"/>
            <use x="3" y="0" xlink:href="#g0-50"/>
        </g>
        </svg>""",
        encoding="utf-8",
    )
    (tmp_path / "doc_text.svg").write_text(
        """<svg xmlns="http://www.w3.org/2000/svg"><text>12</text></svg>""",
        encoding="utf-8",
    )
    processor = TeXDocumentProcessor(TeXDocument().set_defaults().add_to_body("test"))
    processor._tex_path = tmp_path

    glyph_paths, positions = processor._extract_glyph_data()

    assert len(glyph_paths) == 3
    assert positions == [
        ("g0-49", (0, 0), "1", None),
        ("rule-2", (0, 0), None, "rule"),
        ("g0-50", (3, 0), "2", None),
    ]


def test_extract_glyph_data_leaves_characters_unmatched_when_counts_differ(tmp_path):
    svg_file = tmp_path / "doc.svg"
    svg_file.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg"
             xmlns:xlink="http://www.w3.org/1999/xlink">
        <defs><path id="g0-65" d="M0 0 L1 0 L1 1 L0 1 Z"/></defs>
        <g id="page1">
            <use x="0" y="0" xlink:href="#g0-65"/>
            <use x="2" y="0" xlink:href="#g0-65"/>
        </g>
        </svg>""",
        encoding="utf-8",
    )
    (tmp_path / "doc_text.svg").write_text(
        """<svg xmlns="http://www.w3.org/2000/svg"><text>A</text></svg>""",
        encoding="utf-8",
    )
    processor = TeXDocumentProcessor(TeXDocument().set_defaults().add_to_body("test"))
    processor._tex_path = tmp_path

    _, positions = processor._extract_glyph_data()

    assert positions == [
        ("g0-65", (0, 0), None, None),
        ("g0-65", (2, 0), None, None),
    ]
