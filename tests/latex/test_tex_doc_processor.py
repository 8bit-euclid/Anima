import shutil
import subprocess
import threading

import pytest

import anima.latex.tex_doc_processor as processor_module
from anima.latex.tex_doc_processor import TeXDocumentProcessor, _extract_text_glyphs
from anima.latex.tex_document import TeXDocument


def test_dvi_conversions_run_concurrently_and_wait_for_both(tmp_path, monkeypatch):
    processor = TeXDocumentProcessor(TeXDocument().set_defaults().add_to_body("test"))
    processor._tex_path = tmp_path
    barrier = threading.Barrier(2, timeout=5)
    calls = []

    def run(command, **kwargs):
        barrier.wait()
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, stdout="")

    monkeypatch.setattr(processor_module.subprocess, "run", run)
    processor._convert_dvi_to_svg()

    assert len(calls) == 2
    commands = [command for command, _ in calls]
    assert {command[-1] for command in commands} == {str(tmp_path / "doc.svg"), str(tmp_path / "doc_text.svg")}
    assert sum("--no-fonts" in command for command in commands) == 1
    assert all(command[0] == "dvisvgm" and command[-3] == str(tmp_path / "doc.dvi") for command in commands)
    assert all(kwargs["cwd"] == tmp_path and kwargs["check"] is True for _, kwargs in calls)


@pytest.mark.parametrize("failed", [("doc.svg",), ("doc_text.svg",), ("doc.svg", "doc_text.svg")])
def test_dvi_conversion_reports_all_failures_after_both_finish(tmp_path, monkeypatch, failed):
    processor = TeXDocumentProcessor(TeXDocument().set_defaults().add_to_body("test"))
    processor._tex_path = tmp_path
    barrier = threading.Barrier(2, timeout=5)
    completed = []
    logs = []

    def run(command, **kwargs):
        barrier.wait()
        name = command[-1].rsplit("/", 1)[-1]
        completed.append(name)
        if name in failed:
            raise subprocess.CalledProcessError(1, command, output=f"{name} error")
        return subprocess.CompletedProcess(command, 0, stdout="")

    monkeypatch.setattr(processor_module.subprocess, "run", run)
    monkeypatch.setattr(processor_module, "print_logs", lambda _cmd, result: logs.append(result))
    with pytest.raises(RuntimeError, match="DVI to SVG conversion failed") as exc:
        processor._convert_dvi_to_svg()
    assert set(completed) == {"doc.svg", "doc_text.svg"}
    assert all(name in str(exc.value) for name in failed)
    assert len(logs) == 2
    assert sum(isinstance(result, subprocess.CalledProcessError) for result in logs) == len(failed)


def test_processor_cleans_temporary_directory_if_enter_fails(monkeypatch):
    processor = TeXDocumentProcessor(TeXDocument().set_defaults().add_to_body("test"))
    monkeypatch.setattr(processor, "_convert_tex_to_dvi", lambda: None)

    def fail():
        raise RuntimeError("conversion failed")

    monkeypatch.setattr(processor, "_convert_dvi_to_svg", fail)
    with pytest.raises(RuntimeError, match="conversion failed"):
        processor.__enter__()
    assert not processor._tex_path.exists()


@pytest.mark.skipif(
    not shutil.which("lualatex") or not shutil.which("dvisvgm"), reason="LaTeX and dvisvgm are required"
)
def test_concurrent_dvi_conversion_matches_sequential_output(tmp_path):
    document = TeXDocument().set_defaults().add_to_body(r"$\frac{a}{b}+\sum_{i=1}^{n} x_i$")
    processor = TeXDocumentProcessor(document)
    processor._tex_path = tmp_path
    processor._convert_tex_to_dvi()
    processor._convert_dvi_to_svg()
    paths = [tmp_path / "doc.svg", tmp_path / "doc_text.svg"]
    concurrent = [path.read_bytes() for path in paths]
    extracted_paths, extracted_positions = processor._extract_glyph_data()
    for path in paths:
        options = ["--no-fonts"] if path.name == "doc.svg" else []
        subprocess.run(
            ["dvisvgm", *options, "--exact-bbox", "--precision=6", str(tmp_path / "doc.dvi"), "-o", str(path)],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
    assert [path.read_bytes() for path in paths] == concurrent
    paths_after, positions_after = processor._extract_glyph_data()
    assert positions_after == extracted_positions
    assert paths_after == extracted_paths


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
