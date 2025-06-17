import subprocess
import tempfile
import svgpathtools as svgtools
import xml.etree.ElementTree as ET
from pathlib import Path
from functools import partial
from anima.latex.glyph import Glyph, Subpath
from anima.latex.tex_file import TeXFile, DEFAULT_FONT_SIZE
from collections import defaultdict as ddict

TEX_POINT_TO_BL_UNIT = 0.005   # Length (in Blender units) of 1pt (in LaTeX)
SAMPLING_LENGTH = \
    0.01 * DEFAULT_FONT_SIZE * TEX_POINT_TO_BL_UNIT  # For points along glyph curves
TEX_DEBUG_MODE = True  # Print LaTeX and DVI logs to console
SVG_NAMESPACE = \
    {'svg': 'http://www.w3.org/2000/svg'}  # Namespace for SVG elements in XML


class TeXFileProcessor:
    """Processes LaTeX documents to extract glyph data from SVG output.
    Compiles LaTeX to DVI, converts to SVG, and extracts glyph metadata."""

    def __init__(self, content: TeXFile | str):
        """Initialize the converter with LaTeX content.
        Args:
            content: A TeXFile object or string containing LaTeX content (body)."""
        # Use provided latex document or setup a default one
        if isinstance(content, str):
            content = TeXFile().set_defaults()\
                               .add_to_body(content)

        self._text = str(content)
        self._temp_dir: tempfile.TemporaryDirectory = None
        self._tex_path: Path = None  # Path to the temporary directory for LaTeX files
        self._tex_name = "doc"  # Base name for .tex, .dvi, .svg, etc.

    def __enter__(self) -> dict[Glyph]:
        """Context manager to handle LaTeX compilation, SVG generation, and file cleanup.
        Returns:
            A dictionary mapping glyph IDs to Glyph objects."""
        # Create a temporary directory to store the LaTeX, SVG, and other generated files
        self._temp_dir = tempfile.TemporaryDirectory()
        self._tex_path = Path(self._temp_dir.name)

        # Run the LaTeX compilation and conversion to SVG. A JSON file with glyph metadata is also generated.
        self._convert_tex_to_dvi()
        self._convert_dvi_to_svg()

        return self._extract_glyphs(self._get_svg_file())

    def __exit__(self, exc_type, exc_value, traceback):
        self._temp_dir.cleanup()

    def _convert_tex_to_dvi(self):
        """Compile the LaTeX file to DVI format and prepare for glyph extraction.
        Raises:
            RuntimeError: If the LaTeX compilation fails.
        """
        tex_path = self._tex_path
        tex_file = tex_path/f'{self._tex_name}.tex'

        # Write LaTeX content
        if TEX_DEBUG_MODE:
            print(f"Processing LaTeX content:\n{self._text}\n")
        tex_file.write_text(self._text, encoding="utf-8")

        # Run lualatex to generate DVI
        run_proc = partial(subprocess.run, cwd=tex_path,
                           capture_output=True, check=True, text=True)
        cmd = "lualatex"
        try:
            res = run_proc([cmd, "-interaction=nonstopmode",
                            "-output-format=dvi", str(tex_file)])
            print_logs(cmd, res)
        except subprocess.CalledProcessError as err:
            print_logs(cmd, err)
            raise RuntimeError("LaTeX compilation failed.") from err

    def _convert_dvi_to_svg(self):
        """Convert the DVI file to SVG format using dvisvgm.
        Raises:
            RuntimeError: If the DVI to SVG conversion fails."""
        tex_path = self._tex_path
        svg_file = tex_path/f'{self._tex_name}.svg'

        run_proc = partial(subprocess.run, cwd=tex_path,
                           capture_output=True, check=True, text=True)
        cmd = "dvisvgm"
        try:
            dvi_file = tex_path/f'{self._tex_name}.dvi'
            res = run_proc([cmd, "--no-fonts", "--exact-bbox", "--precision=6",
                            str(dvi_file), "-o", str(svg_file)])
            print_logs(cmd, res)
        except subprocess.CalledProcessError as err:
            print_logs(cmd, err)
            raise RuntimeError("DVI to SVG conversion failed.") from err

    def _get_svg_file(self) -> Path:
        """Get the SVG file generated from the LaTeX document.
        Raises:
            RuntimeError: If the SVG file is not found."""
        svg_file = self._tex_path/f'{self._tex_name}.svg'
        if not svg_file.exists():
            raise RuntimeError(f"SVG file '{svg_file}' not found. "
                               "Ensure that the DVI to SVG conversion was successful.")
        if TEX_DEBUG_MODE:
            # Print contents of the SVG file for debugging
            with open(svg_file, 'r', encoding='utf-8') as f:
                print(f"SVG file content:\n\n{f.read()}")
        return svg_file

    def _extract_glyphs(self, svg_file: Path) -> dict[Glyph]:
        """Extract cubic Bézier curves and bounding boxes using svgpathtools.
        Args:
            svg_file: Path to the SVG file generated from the LaTeX document.
        Returns:
            A dictionary mapping glyph IDs to Glyph objects, each containing its subpaths and positions."""

        all_paths, all_attrs = svgtools.svg2paths(svg_file)

        # Create all unique Glyph objects
        glyphs = dict()
        for path, attrs in zip(all_paths, all_attrs):
            id = attrs['id']
            subpaths = path.continuous_subpaths()
            glyphs[id] = Glyph([Subpath(path) for path in subpaths])

        # Store the positions of the instances of each glyph.
        positions: ddict[str, list[tuple[float, float]]] = ddict(list)
        tree = ET.parse(svg_file)
        root = tree.getroot()
        for use in root.findall('.//svg:use', SVG_NAMESPACE):
            gid = use.attrib['{http://www.w3.org/1999/xlink}href'][1:]
            assert gid in glyphs, f"Glyph ID '{gid}' not found in the glyphs dict."

            x = float(use.attrib.get('x', 0))
            y = float(use.attrib.get('y', 0))
            positions[gid].append((x, -y))  # Invert y-coordinate

        return glyphs


def signed_area(points):
    """Calculate the signed area of a polygon defined by a list of points.
    Args:
        points: A list of(x, y) tuples representing the vertices of the polygon.
    Returns:
        The signed area of the polygon. Positive if the points are ordered counter-clockwise, negative if clockwise.
    """
    # points: list of (x, y) tuples
    return 0.5 * sum((x1 * y2 - x2 * y1)
                     for (x1, y1), (x2, y2) in zip(points, points[1:] + [points[0]]))


def is_inner_loop(points):
    """Determine if the given points form an inner loop(clockwise order).
    Args:
        points: A list of(x, y) tuples representing the vertices of the polygon.
    Returns:
        True if the points are ordered clockwise(inner loop), else False (outer loop).
    """
    return signed_area(points) < 0  # negative = clockwise


def print_logs(command: str, result: subprocess.CompletedProcess | subprocess.CalledProcessError):
    """Print the stdout and stderr result of a subprocess.

    Args:
        command: The command that was run.
        result: The result of the subprocess run, which can be a CompletedProcess or CalledProcessError."""
    if isinstance(result, subprocess.CompletedProcess) and not TEX_DEBUG_MODE:
        return

    for name in ('stdout', 'stderr'):
        output = getattr(result, name, '')
        if output and output.strip():
            print(f"{command} {name}:\n{output}")
