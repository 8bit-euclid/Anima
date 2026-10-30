import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from functools import partial
from pathlib import Path

import svgpathtools as svgtools

from anima.diagnostics import format_output, logger
from anima.latex.tex_document import TeXDocument

TEX_DEBUG_MODE = True  # Print LaTeX and DVI logs to console
SVG_NAMESPACE = {"svg": "http://www.w3.org/2000/svg"}  # Namespace for SVG elements in XML

GlyphPathsType = dict[str, svgtools.Path]  # Maps glyph IDs to their SVG paths
GlyphPositionsType = list[tuple[str, tuple[float, float], str | None, str | None]]
# (glyph ID, (x, y), character, optional display label)


class TeXDocumentProcessor:
    """Processes LaTeX documents to extract glyph data from SVG output.
    Compiles LaTeX to DVI, converts to SVG, and extracts glyph metadata."""

    def __init__(self, texfile: TeXDocument):
        """Initialize the converter with LaTeX content.

        Args:
            texfile: A TeXFile object containing LaTeX content.
        """
        assert isinstance(texfile, TeXDocument), "Content must be a TeXFile instance."
        self._content = str(texfile)
        self._temp_dir: tempfile.TemporaryDirectory = None
        self._tex_path: Path = None  # Path to the temporary directory for LaTeX files
        self._tex_name = "doc"  # Base name for .tex, .dvi, .svg, etc.

    def __enter__(self) -> tuple[GlyphPathsType, GlyphPositionsType]:
        """Context manager to handle LaTeX compilation, SVG generation, and file cleanup.

        Returns:
            A tuple containing:
            - A dictionary mapping glyph IDs to their (unique) SVG paths.
            - Ordered glyph IDs, positions (x, y), characters, and optional display labels.
        """
        # Create a temporary directory to store the LaTeX, SVG, and other generated files
        self._temp_dir = tempfile.TemporaryDirectory()
        self._tex_path = Path(self._temp_dir.name)

        # Keep outline geometry and font/text metadata in separate SVG outputs.
        self._convert_tex_to_dvi()
        self._convert_dvi_to_svg()

        return self._extract_glyph_data()

    def __exit__(self, exc_type, exc_value, traceback):
        """Cleanup temporary files after processing."""
        self._temp_dir.cleanup()

    def _convert_tex_to_dvi(self):
        """Compile the LaTeX file to DVI format and prepare for glyph extraction.

        Raises:
            RuntimeError: If the LaTeX compilation fails.
        """
        tex_path = self._tex_path
        tex_file = tex_path / f"{self._tex_name}.tex"

        # Write LaTeX content
        logger.trace(format_output("LaTeX document content", self._content))
        tex_file.write_text(self._content, encoding="utf-8")

        # Run lualatex to generate DVI
        logger.info("Compiling TeX to DVI...")
        run_proc = partial(
            subprocess.run,
            cwd=tex_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            #    capture_output=True,
            check=True,
            text=True,
        )
        cmd = "lualatex"
        try:
            res = run_proc([cmd, "-interaction=nonstopmode", "-output-format=dvi", str(tex_file)])
            print_logs(cmd, res)
        except subprocess.CalledProcessError as err:
            print_logs(cmd, err)
            raise RuntimeError("LaTeX compilation failed.") from err

    def _convert_dvi_to_svg(self):
        """Convert the DVI file to SVG format using dvisvgm.

        Raises:
            RuntimeError: If the DVI to SVG conversion fails.
        """
        tex_path = self._tex_path

        logger.info("Compiling DVI to SVG...")
        run_proc = partial(
            subprocess.run,
            cwd=tex_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            #    capture_output=True,
            check=True,
            text=True,
        )
        cmd = "dvisvgm"
        dvi_file = tex_path / f"{self._tex_name}.dvi"
        # Outlining is required for Blender geometry; font output preserves character-to-font mappings.
        outputs = (
            (self._get_svg_path(), ["--no-fonts"]),
            (self._get_svg_path("_text"), []),
        )
        for svg_file, options in outputs:
            try:
                res = run_proc(
                    [
                        cmd,
                        *options,
                        "--exact-bbox",
                        "--precision=6",
                        str(dvi_file),
                        "-o",
                        str(svg_file),
                    ]
                )
                print_logs(cmd, res)
            except subprocess.CalledProcessError as err:
                print_logs(cmd, err)
                raise RuntimeError("DVI to SVG conversion failed.") from err

    def _get_svg_file(self) -> Path:
        """Get the SVG file generated from the LaTeX document.

        Returns:
            Path: The path to the SVG file.

        Raises:
            RuntimeError: If the SVG file is not found.
        """
        svg_file = self._get_svg_path()
        if not svg_file.exists():
            raise RuntimeError(
                f"SVG file '{svg_file}' not found. Ensure that the DVI to SVG conversion was successful."
            )
        # Print contents of the SVG file for debugging
        with open(svg_file, encoding="utf-8") as f:
            logger.trace(format_output("SVG file content", f.read()))
        return svg_file

    def _get_svg_path(self, suffix: str = "") -> Path:
        """Build the path for an SVG output from the document name.

        Args:
            suffix: Optional suffix to append to the base document name.

        Returns:
            Path: The path to the SVG file.
        """
        return self._tex_path / f"{self._tex_name}{suffix}.svg"

    def _extract_glyph_data(self) -> tuple[GlyphPathsType, GlyphPositionsType]:
        """Extract reusable outlines and ordered glyph instances from the generated SVGs.

        Returns:
            A pair containing:
            - A mapping from SVG glyph IDs (and generated rule IDs) to outline paths.
            - Ordered instances as ``(path_id, (x, y), character, display_label)``.

            Positions use Blender's y-axis direction. Character and display label
            are None when no matching text metadata or special-shape label exists.

        Notes:
            Character metadata is paired with outline instances in SVG use-element
            order when their counts match. A mismatch is logged and leaves the
            character metadata unavailable. Standalone rectangles recognized in
            both SVGs are included as fraction-rule instances; unsupported
            anonymous paths are ignored.
        """
        logger.info("Extracting glyph data from SVG...")
        svg_file = self._get_svg_file()
        all_paths, all_attrs = svgtools.svg2paths(svg_file)

        # dvisvgm stores reusable glyph outlines as identified paths. Fraction bars
        # are emitted separately as rectangles, so assign them generated path IDs.
        glyph_paths = GlyphPathsType()
        rule_paths: dict[tuple[str, str, str, str], list[str]] = {}
        for path, attrs in zip(all_paths, all_attrs):
            gid = attrs.get("id")
            if gid is not None:
                glyph_paths[gid] = path
            elif {"x", "y", "width", "height"} <= attrs.keys():
                rule_id = f"rule-{len(glyph_paths)}"
                glyph_paths[rule_id] = path
                signature = tuple(attrs[key] for key in ("x", "y", "width", "height"))
                rule_paths.setdefault(signature, []).append(rule_id)
            else:
                logger.debug("Ignoring SVG path without an ID or recognized standalone shape attributes.")

        tree = ET.parse(svg_file)
        root = tree.getroot()

        uses = root.findall(".//svg:use", SVG_NAMESPACE)
        text_glyphs = _extract_text_glyphs(self._get_svg_path("_text"))
        if len(text_glyphs) == len(uses):
            text_glyphs_by_use = text_glyphs
        else:
            # Only pair by position when both SVG conversions produced the same
            # number of glyph instances; otherwise labels could be misleading.
            logger.warning(
                "Could not match SVG text characters to glyphs: found {} characters for {} glyphs.",
                len(text_glyphs),
                len(uses),
            )
            text_glyphs_by_use = [(None, None)] * len(uses)

        # Walk the outline SVG, rather than grouping uses and rectangles, to keep
        # generated Blender object order consistent with the rendered expression.
        glyph_positions = GlyphPositionsType()
        use_index = 0
        for element in root.iter():
            tag = element.tag.rsplit("}", 1)[-1]
            if tag == "use":
                gid = element.attrib["{http://www.w3.org/1999/xlink}href"][1:]
                assert gid in glyph_paths, f"Glyph with ID '{gid}' not found."

                x = float(element.attrib.get("x", 0))
                y = float(element.attrib.get("y", 0))
                character, display_label = text_glyphs_by_use[use_index]
                glyph_positions.append((gid, (x, -y), character, display_label))
                use_index += 1
            elif tag == "rect":
                signature = tuple(element.attrib.get(key, "") for key in ("x", "y", "width", "height"))
                matching_rules = rule_paths.get(signature)
                if matching_rules:
                    rule_id = matching_rules.pop(0)
                    glyph_positions.append((rule_id, (0, 0), None, "rule"))

        return glyph_paths, glyph_positions


def _extract_text_glyphs(svg_file: Path) -> list[tuple[str | None, str | None]]:
    """Read rendered characters and private-use glyph names from a dvisvgm SVG.

    Args:
        svg_file: Font-preserving SVG produced by dvisvgm.

    Returns:
        Non-whitespace text characters in SVG reading order, each paired with a
        font ``glyph-name`` when that character is in a Unicode private-use area
        and the SVG provides a matching font mapping. Other characters, or
        private-use characters without a font mapping, have a None glyph name.

    Notes:
        The character-to-font mapping is selected using each text element's CSS
        class and the corresponding ``font-family`` rule in the SVG stylesheet.
        Nested text elements are read as part of their containing text element.
    """
    root = ET.parse(svg_file).getroot()
    font_names: dict[str, dict[str, str]] = {}
    for font in root.iter():
        if font.tag.rsplit("}", 1)[-1] != "font":
            continue
        font_face = next(
            (child for child in font if child.tag.rsplit("}", 1)[-1] == "font-face"),
            None,
        )
        family = (
            font_face.attrib.get("font-family", font.attrib.get("id", ""))
            if font_face is not None
            else font.attrib.get("id", "")
        )
        # Glyph names are font-specific; a Unicode value alone is not unique
        # across the multiple math fonts dvisvgm may embed.
        glyph_names = font_names.setdefault(family, {})
        for glyph in font:
            if glyph.tag.rsplit("}", 1)[-1] == "glyph":
                character = glyph.attrib.get("unicode")
                glyph_name = glyph.attrib.get("glyph-name")
                if character and glyph_name:
                    glyph_names[character] = glyph_name

    text_families: dict[str, str] = {}
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] != "style" or element.text is None:
            continue
        # dvisvgm associates text classes with font families through CSS rules.
        for css_class, family in re.findall(r"text\.([^{\s]+)\s*\{[^}]*font-family:\s*([^;}\s]+)", element.text):
            text_families[css_class] = family.strip("'\"")

    text_glyphs: list[tuple[str, str | None]] = []
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] == "text":
            css_class = element.attrib.get("class", "")
            family = text_families.get(css_class, "")
            glyph_names = font_names.get(family, {})
            # Text may be split across nested tspans; flatten it while excluding
            # whitespace, which has no corresponding outline glyph.
            text_glyphs.extend(
                (character, glyph_names.get(character) if _is_private_use_character(character) else None)
                for character in "".join(element.itertext())
                if not character.isspace()
            )
    return text_glyphs


def _is_private_use_character(character: str) -> bool:
    """Return whether a character belongs to a Unicode private-use area.

    Args:
        character: The character to check.

    Returns:
        True if the character is in a private-use area, False otherwise.
    """
    codepoint = ord(character)
    return 0xE000 <= codepoint <= 0xF8FF or 0xF0000 <= codepoint <= 0xFFFFD or 0x100000 <= codepoint <= 0x10FFFD


def print_logs(command: str, result: subprocess.CompletedProcess | subprocess.CalledProcessError):
    """Print the stdout and stderr result of a subprocess.

    Args:
        command: The command that was run.
        result: The result of the subprocess run, which can be a CompletedProcess or CalledProcessError.
    """
    if isinstance(result, subprocess.CompletedProcess) and not TEX_DEBUG_MODE:
        return

    output = getattr(result, "stdout", "")
    if output.rstrip():
        logger.trace(format_output(f"{command.capitalize()} output", output))
