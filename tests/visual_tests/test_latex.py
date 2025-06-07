import subprocess
import tempfile
import svgpathtools as svgtools
import xml.etree.ElementTree as ET
from pathlib import Path
from functools import partial
from anima.latex.glyph import Glyph, Subpath
from anima.latex.tex_file import TeXFile, DEFAULT_FONT_SIZE

TEX_POINT_TO_BL_UNIT = 0.005   # Length (in Blender units) of 1pt (in LaTeX)
SAMPLING_LENGTH = \
    0.01 * DEFAULT_FONT_SIZE * TEX_POINT_TO_BL_UNIT  # For points along glyph curves
PRINT_LOGS = False  # Print LaTeX and DVI logs to console


class TeXtoSVGConverter:
    def __init__(self, content: str | TeXFile):
        # Use provided latex document or setup a default one
        if isinstance(content, str):
            content = TeXFile().set_defaults()\
                               .add_text(content)

        self.content_str = str(content)
        self.tmp_dir = None

    def __enter__(self) -> dict[Glyph]:
        """Context manager to handle LaTeX compilation, SVG generation, and file cleanup.
        Returns:
            A dictionary mapping glyph IDs to Glyph objects."""
        # Create a temporary directory to store the LaTeX, SVG, and other generated files
        self.tmp_dir = tempfile.TemporaryDirectory()
        tmp_path = Path(self.tmp_dir.name)
        tex_file = tmp_path/"doc.tex"
        dvi_file = tmp_path/"doc.dvi"
        svg_file = tmp_path/"doc.svg"

        # Write LaTeX content
        tex_file.write_text(self.content_str, encoding="utf-8")

        # Run lualatex to generate DVI
        run_proc = partial(subprocess.run, cwd=tmp_path,
                           capture_output=True, check=True, text=True)
        cmd = "lualatex"
        try:
            res = run_proc([cmd, "-interaction=nonstopmode",
                           "-output-format=dvi", str(tex_file)])
            print_logs(cmd, res)
        except subprocess.CalledProcessError as err:
            print_logs(cmd, err)
            raise RuntimeError("LaTeX compilation failed.") from err

        # Convert DVI to SVG
        cmd = "dvisvgm"
        try:
            res = run_proc([cmd, "--no-fonts", "--exact-bbox", "--precision=6",
                           str(dvi_file), "-o", str(svg_file)])
            print_logs(cmd, res)
        except subprocess.CalledProcessError as err:
            print_logs(cmd, err)
            raise RuntimeError("DVI to SVG conversion failed.") from err

        # print("DVI file content:\n")
        # read_dvi_file(str(dvi_file))

        # Print contents of the SVG file for debugging
        with open(svg_file, 'r', encoding='utf-8') as f:
            print(f"SVG file content:\n{f.read()}")

        return self._extract_glyphs(svg_file)

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
        tree = ET.parse(svg_file)
        root = tree.getroot()
        ns = {'svg': 'http://www.w3.org/2000/svg'}
        for use in root.findall('.//svg:use', ns):
            gid = use.attrib['{http://www.w3.org/1999/xlink}href'][1:]
            assert gid in glyphs, f"Glyph ID '{gid}' not found in the glyphs dict."

            x = float(use.attrib.get('x', 0))
            y = float(use.attrib.get('y', 0))
            glyphs[gid].positions.append((x, -y))  # Invert y-coordinate

        return glyphs

    def __exit__(self, exc_type, exc_value, traceback):
        self.tmp_dir.cleanup()


def print_logs(command: str, result: subprocess.CompletedProcess | subprocess.CalledProcessError):
    """Print the stdout and stderr result of a subprocess.

    Args:
        command: The command that was run.
        result: The result of the subprocess run, which can be a CompletedProcess or CalledProcessError."""
    if isinstance(result, subprocess.CompletedProcess) and not PRINT_LOGS:
        return

    if result.stdout.strip():
        print(command + " output:\n")
        print(result.stdout)
    if result.stderr.strip():
        print(command + " errors:\n")
        print(result.stderr)


def signed_area(points):
    """Calculate the signed area of a polygon defined by a list of points.
    Args:
        points: A list of (x, y) tuples representing the vertices of the polygon.
    Returns:        
        The signed area of the polygon. Positive if the points are ordered counter-clockwise, negative if clockwise.
    """
    # points: list of (x, y) tuples
    return 0.5 * sum((x1 * y2 - x2 * y1)
                     for (x1, y1), (x2, y2) in zip(points, points[1:] + [points[0]]))


def is_inner_loop(points):
    """Determine if the given points form an inner loop (clockwise order).
    Args:
        points: A list of (x, y) tuples representing the vertices of the polygon.
    Returns:
        True if the points are ordered clockwise (inner loop), else False (outer loop).
    """
    return signed_area(points) < 0  # negative = clockwise


def test_text_to_glyphs():
    # text = r'Lyy\\y'
    # text = 'T'
    # text = 'S'
    # text = 'Hello World!'
    text = 'office'
    # text = '$E = mc^2$'
    # text = r'boob\\y'
    # text = 'C'
    # text = '8'
    # text = 'O{\Huge 8}'
    # text = 'O'
    # text = 'Aghhhgg!!aaGH'
    with TeXtoSVGConverter(text) as glyphs:
        for glyph in glyphs.values():
            glyph.create_curves()
            glyph.create_mesh()
            # glyph.create_instances()
