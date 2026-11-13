from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest

import anima.latex.tex_document_processor as processor_module
from anima.latex.tex_cache import (
    CachedTexOutputs,
    clear_tex_cache,
    read_tex_cache,
    tex_cache_enabled,
    tex_cache_key,
    tex_cache_root,
    write_tex_cache,
)
from anima.latex.tex_document import TeXDocument
from anima.latex.tex_document_processor import TeXDocumentProcessor

OUTLINE_SVG = b"<svg>outline</svg>"
TEXT_SVG = b"<svg>text</svg>"


def _processor(document: str = "cache test") -> TeXDocumentProcessor:
    return TeXDocumentProcessor(TeXDocument().set_defaults().add_to_body(document))


def _install_fake_pipeline(
    monkeypatch: pytest.MonkeyPatch,
    outputs: tuple[bytes, bytes] = (OUTLINE_SVG, TEXT_SVG),
) -> list[str]:
    calls: list[str] = []

    def compile_tex(self: TeXDocumentProcessor) -> None:
        calls.append("lualatex")
        self._command_logs.append(("lualatex", "compiler warning\n"))

    def convert_dvi(self: TeXDocumentProcessor) -> None:
        calls.append("dvisvgm")
        self._command_logs.extend((("dvisvgm", "outline notice\n"), ("dvisvgm", "")))
        self._get_svg_path().write_bytes(outputs[0])
        self._get_svg_path("_text").write_bytes(outputs[1])

    def extract(self: TeXDocumentProcessor) -> tuple[bytes, bytes]:
        return (
            self._get_svg_path().read_bytes(),
            self._get_svg_path("_text").read_bytes(),
        )

    monkeypatch.setattr(TeXDocumentProcessor, "_convert_tex_to_dvi", compile_tex)
    monkeypatch.setattr(TeXDocumentProcessor, "_convert_dvi_to_svg", convert_dvi)
    monkeypatch.setattr(TeXDocumentProcessor, "_extract_glyph_data", extract)
    return calls


def _cached_entries(root: Path) -> list[Path]:
    return list(root.glob("v*/[0-9a-f]*.json"))


def test_processor_reuses_paired_svg_cache_without_running_tools(tmp_path, monkeypatch):
    monkeypatch.setenv("ANIMA_TEX_CACHE_DIR", str(tmp_path))
    monkeypatch.delenv("ANIMA_DISABLE_TEX_CACHE", raising=False)
    calls = _install_fake_pipeline(monkeypatch)
    replayed_logs = []
    monkeypatch.setattr(
        processor_module,
        "_print_captured_output",
        lambda command, output: replayed_logs.append((command, output)),
    )

    with _processor() as first:
        assert first == (OUTLINE_SVG, TEXT_SVG)
    with _processor() as second:
        assert second == (OUTLINE_SVG, TEXT_SVG)

    assert calls == ["lualatex", "dvisvgm"]
    assert len(_cached_entries(tmp_path)) == 1
    assert replayed_logs == [
        ("lualatex", "compiler warning\n"),
        ("dvisvgm", "outline notice\n"),
        ("dvisvgm", ""),
    ]


def test_processor_cache_key_includes_complete_document(tmp_path, monkeypatch):
    monkeypatch.setenv("ANIMA_TEX_CACHE_DIR", str(tmp_path))
    monkeypatch.delenv("ANIMA_DISABLE_TEX_CACHE", raising=False)
    calls = _install_fake_pipeline(monkeypatch)

    with _processor("first expression"):
        pass
    with _processor("second expression"):
        pass

    assert calls == ["lualatex", "dvisvgm", "lualatex", "dvisvgm"]
    assert len(_cached_entries(tmp_path)) == 2


def test_disabled_cache_does_not_read_or_write_entries(tmp_path, monkeypatch):
    monkeypatch.setenv("ANIMA_TEX_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("ANIMA_DISABLE_TEX_CACHE", "1")
    calls = _install_fake_pipeline(monkeypatch)

    with _processor():
        pass
    with _processor():
        pass

    assert calls == ["lualatex", "dvisvgm", "lualatex", "dvisvgm"]
    assert not _cached_entries(tmp_path)


def test_invalid_cache_disable_setting_is_reported(monkeypatch):
    monkeypatch.setenv("ANIMA_DISABLE_TEX_CACHE", "sometimes")

    with pytest.raises(ValueError, match="ANIMA_DISABLE_TEX_CACHE"):
        tex_cache_enabled()


def test_cache_is_enabled_by_default(monkeypatch):
    monkeypatch.delenv("ANIMA_DISABLE_TEX_CACHE", raising=False)

    assert tex_cache_enabled()


def test_corrupt_cache_entry_is_rebuilt(tmp_path, monkeypatch):
    monkeypatch.setenv("ANIMA_TEX_CACHE_DIR", str(tmp_path))
    monkeypatch.delenv("ANIMA_DISABLE_TEX_CACHE", raising=False)
    processor = _processor()
    key = tex_cache_key(processor._content)
    path = tmp_path / "v1" / f"{key}.json"
    path.parent.mkdir(parents=True)
    path.write_text("{", encoding="utf-8")
    calls = _install_fake_pipeline(monkeypatch)

    with processor as outputs:
        assert outputs == (OUTLINE_SVG, TEXT_SVG)

    assert calls == ["lualatex", "dvisvgm"]
    cached = read_tex_cache(tmp_path, key)
    assert cached == CachedTexOutputs(
        OUTLINE_SVG,
        TEXT_SVG,
        (("lualatex", "compiler warning\n"), ("dvisvgm", "outline notice\n"), ("dvisvgm", "")),
    )


@pytest.mark.parametrize("stage", ["lualatex", "dvisvgm", "extract"])
def test_failed_tex_processing_does_not_create_cache_entry(tmp_path, monkeypatch, stage):
    monkeypatch.setenv("ANIMA_TEX_CACHE_DIR", str(tmp_path))
    monkeypatch.delenv("ANIMA_DISABLE_TEX_CACHE", raising=False)

    def fail(_self):
        raise RuntimeError(f"{stage} failed")

    if stage == "lualatex":
        monkeypatch.setattr(TeXDocumentProcessor, "_convert_tex_to_dvi", fail)
    elif stage == "dvisvgm":
        _install_fake_pipeline(monkeypatch)
        monkeypatch.setattr(TeXDocumentProcessor, "_convert_dvi_to_svg", fail)
    else:
        _install_fake_pipeline(monkeypatch)
        monkeypatch.setattr(TeXDocumentProcessor, "_extract_glyph_data", fail)

    with pytest.raises(RuntimeError, match=f"{stage} failed"), _processor():
        pass

    assert not _cached_entries(tmp_path)


def test_concurrent_cache_writers_publish_a_complete_svg_pair(tmp_path):
    key = tex_cache_key("concurrent")
    pairs = [(f"<svg>{index}</svg>".encode(), f"<svg>text-{index}</svg>".encode()) for index in range(12)]

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(write_tex_cache, tmp_path, key, *pair) for pair in pairs]
        for future in futures:
            future.result()

    cached = read_tex_cache(tmp_path, key)
    assert cached is not None
    assert (cached.outline_svg, cached.text_svg) in pairs
    assert len(_cached_entries(tmp_path)) == 1


def test_concurrent_readers_never_observe_a_partial_pair(tmp_path):
    key = tex_cache_key("concurrent read")
    pairs = [(f"<svg>{index}</svg>".encode(), f"<svg>text-{index}</svg>".encode()) for index in range(12)]
    write_tex_cache(tmp_path, key, *pairs[0])
    barrier = Barrier(2)

    def write_entries():
        barrier.wait()
        for pair in pairs[1:]:
            write_tex_cache(tmp_path, key, *pair)

    def read_entries():
        barrier.wait()
        return [read_tex_cache(tmp_path, key) for _ in range(50)]

    with ThreadPoolExecutor(max_workers=2) as executor:
        writer = executor.submit(write_entries)
        reader = executor.submit(read_entries)
        writer.result()
        observed = reader.result()

    assert observed
    assert all(entry is not None and (entry.outline_svg, entry.text_svg) in pairs for entry in observed)


def test_cache_pruning_keeps_storage_within_entry_limit(tmp_path, monkeypatch):
    import anima.latex.tex_cache as cache_module

    monkeypatch.setattr(cache_module, "_MAX_CACHE_ENTRIES", 2)
    for index in range(4):
        key = tex_cache_key(f"expression {index}")
        write_tex_cache(tmp_path, key, OUTLINE_SVG, TEXT_SVG)

    assert len(_cached_entries(tmp_path)) <= 2


def test_cache_pruning_keeps_storage_within_byte_limit(tmp_path, monkeypatch):
    import anima.latex.tex_cache as cache_module

    monkeypatch.setattr(cache_module, "_MAX_CACHE_BYTES", 500)
    for index in range(4):
        key = tex_cache_key(f"expression {index}")
        write_tex_cache(tmp_path, key, OUTLINE_SVG, TEXT_SVG)

    assert sum(path.stat().st_size for path in _cached_entries(tmp_path)) <= 500


def test_cache_skips_entries_over_the_per_entry_limit(tmp_path, monkeypatch):
    import anima.latex.tex_cache as cache_module

    monkeypatch.setattr(cache_module, "_MAX_ENTRY_BYTES", 128)
    write_tex_cache(tmp_path, tex_cache_key("large"), OUTLINE_SVG, TEXT_SVG)

    assert not _cached_entries(tmp_path)


def test_clear_tex_cache_removes_only_cache_entries(tmp_path):
    key = tex_cache_key("clear")
    write_tex_cache(tmp_path, key, OUTLINE_SVG, TEXT_SVG)
    unrelated = tmp_path / "v1" / "notes.json"
    unrelated.write_text("keep", encoding="utf-8")

    clear_tex_cache(tmp_path)

    assert not _cached_entries(tmp_path)
    assert unrelated.read_text(encoding="utf-8") == "keep"


def test_cache_root_uses_configured_path(tmp_path, monkeypatch):
    monkeypatch.setenv("ANIMA_TEX_CACHE_DIR", str(tmp_path))

    assert tex_cache_root() == tmp_path


def test_cache_write_failure_does_not_hide_successful_tex_processing(tmp_path, monkeypatch):
    monkeypatch.setenv("ANIMA_TEX_CACHE_DIR", str(tmp_path))
    monkeypatch.delenv("ANIMA_DISABLE_TEX_CACHE", raising=False)
    _install_fake_pipeline(monkeypatch)

    def fail_write(*_args):
        raise OSError("cache is unavailable")

    monkeypatch.setattr(processor_module, "write_tex_cache", fail_write)
    with _processor() as result:
        assert result == (OUTLINE_SVG, TEXT_SVG)


def test_cache_key_is_stable_and_content_and_pipeline_sensitive(monkeypatch):
    import anima.latex.tex_cache as cache_module

    assert tex_cache_key("same") == tex_cache_key("same")
    assert tex_cache_key("same") != tex_cache_key("changed")

    pipeline_key = tex_cache_key("same")
    monkeypatch.setattr(cache_module, "_CACHE_PIPELINE", (*cache_module._CACHE_PIPELINE, ("tool", "--option")))
    assert tex_cache_key("same") != pipeline_key

    small = str(TeXDocument().set_defaults().add_to_body("text", font_size=7.5))
    large = str(TeXDocument().set_defaults().add_to_body("text", font_size=15))
    assert tex_cache_key(small) != tex_cache_key(large)
