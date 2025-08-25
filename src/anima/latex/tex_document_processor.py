import subprocess
import tempfile
import xml.etree.ElementTree as ET
from functools import partial
from pathlib import Path

import svgpathtools as svgtools

from anima.diagnostics import format_output, logger
from anima.latex.tex_document import DEFAULT_FONT_SIZE, TeXDocument

TEX_POINT_TO_BL_UNIT = 0.005  # Length (in Blender units) of 1pt (in LaTeX)
SAMPLING_LENGTH = 0.01 * DEFAULT_FONT_SIZE * TEX_POINT_TO_BL_UNIT  # For points along glyph curves
TEX_DEBUG_MODE = True  # Print LaTeX and DVI logs to console
SVG_NAMESPACE = {"svg": "http://www.w3.org/2000/svg"}  # Namespace for SVG elements in XML

GlyphPathsType = dict[str, svgtools.Path]  # Maps glyph IDs to their SVG paths
GlyphPositionsType = list[tuple[str, tuple[float, float]]]  # List of (glyph ID, (x, y)) tuples


class TeXDocumentProcessor:
    """Processes LaTeX documents to extract glyph data from SVG output.
    Compiles LaTeX to DVI, converts to SVG, and extracts glyph metadata."""

    def __init__(self, texfile: TeXDocument):
        """Initialize the converter with LaTeX content.
        Args:
            texfile: A TeXFile object containing LaTeX content."""
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
                - A list of ordered glyph IDs and their positions (x, y).
        """
        # Create a temporary directory to store the LaTeX, SVG, and other generated files
        self._temp_dir = tempfile.TemporaryDirectory()
        self._tex_path = Path(self._temp_dir.name)

        # Run the LaTeX compilation and conversion to SVG. A JSON file with glyph metadata is also generated.
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
            RuntimeError: If the DVI to SVG conversion fails."""
        tex_path = self._tex_path
        svg_file = tex_path / f"{self._tex_name}.svg"

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
        try:
            dvi_file = tex_path / f"{self._tex_name}.dvi"
            res = run_proc(
                [
                    cmd,
                    "--no-fonts",
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
            RuntimeError: If the SVG file is not found."""
        svg_file = self._tex_path / f"{self._tex_name}.svg"
        if not svg_file.exists():
            raise RuntimeError(
                f"SVG file '{svg_file}' not found. " "Ensure that the DVI to SVG conversion was successful."
            )
        # Print contents of the SVG file for debugging
        with open(svg_file, "r", encoding="utf-8") as f:
            logger.trace(format_output(f"SVG file content", f.read()))
        return svg_file

    def _extract_glyph_data(self) -> tuple[GlyphPathsType, GlyphPositionsType]:
        """Extract cubic Bézier curves and bounding boxes using svgpathtools.
        Returns:
            A tuple containing:
                - A dictionary mapping glyph IDs to their (unique) SVG paths.
                - A list of ordered glyph IDs and their positions (x, y).
        Raises:
            RuntimeError: If the SVG file cannot be processed or glyphs are not found.
        """
        logger.info("Extracting glyph data from SVG...")
        svg_file = self._get_svg_file()
        all_paths, all_attrs = svgtools.svg2paths(svg_file)

        # Create all unique Glyph objects
        glyph_paths = GlyphPathsType()
        for path, attrs in zip(all_paths, all_attrs):
            gid = attrs["id"]
            glyph_paths[gid] = path

        # Store the positions of the instances of each glyph.
        glyph_positions = GlyphPositionsType()
        tree = ET.parse(svg_file)
        root = tree.getroot()
        for use in root.findall(".//svg:use", SVG_NAMESPACE):
            gid = use.attrib["{http://www.w3.org/1999/xlink}href"][1:]
            assert gid in glyph_paths, f"Glyph with ID '{gid}' not found."

            x = float(use.attrib.get("x", 0))
            y = float(use.attrib.get("y", 0))
            glyph_positions.append((gid, (x, -y)))  # Invert y-coordinate

        return glyph_paths, glyph_positions


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
