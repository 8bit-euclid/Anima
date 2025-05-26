import subprocess
import tempfile
import svgpathtools as svgtools
import xml.etree.ElementTree as ET
from pathlib import Path
from anima.primitives.bezier import BezierCurve
from anima.primitives.lines import Line, Segment


class Subpath:
    def __init__(self, path, curves):
        self.path = path  # SVG Path object
        self.curves = curves  # Anima curves


class Glyph:
    def __init__(self, id, path):
        self.id = id
        self.path = path  # shape: [n_segs]
        self.base_curves = []  # shape: [n_segs]
        self.positions = []  # shape: [(x, y) * n_posi]
        self.instances = []  # shape: [[n_segs] * n_posi]
        self.bbox = None


class TeXtoSVG:
    def __init__(self, text):
        doc_class = r'\documentclass[preview]{standalone}'
        preamble = ''
        begin = r'\begin{document}'
        end = r'\end{document}'

        self.tex_content = '\n\n'.join([doc_class, preamble, begin, text, end])
        self.temp_dir = None

    def __enter__(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        temp_path = Path(self.temp_dir.name)
        tex_file = temp_path/"doc.tex"
        dvi_file = temp_path/"doc.dvi"
        svg_file = temp_path/"doc.svg"

        # Write LaTeX content
        tex_file.write_text(self.tex_content, encoding="utf-8")

        try:
            # Run pdflatex to generate DVI
            subprocess.run(["latex", "-interaction=nonstopmode",
                            "-output-format=dvi", str(tex_file)],
                           cwd=temp_path, capture_output=True, check=True)
            # Convert DVI to SVG
            subprocess.run(["dvisvgm", "--no-fonts", "--exact-bbox", str(dvi_file), "-o", str(svg_file)],
                           cwd=temp_path, capture_output=True, check=True)

        except subprocess.CalledProcessError as e:
            raise RuntimeError("LaTeX compilation failed.") from e

        return self._extract_glyphs(svg_file)

    def _extract_glyphs(self, svg_file):
        """Extract cubic Bézier curves and bounding boxes using svgpathtools."""
        all_paths, all_attrs = svgtools.svg2paths(svg_file)

        # Create all unique Glyph objects
        glyphs = []
        for path, attrs in zip(all_paths, all_attrs):
            subpaths = path.continuous_subpaths()
            for sp in subpaths:
                print(sp.iscontinuous())
            glyphs.append(Glyph(attrs['id'], path))

        print('---------------------------------')

        tree = ET.parse(svg_file)
        root = tree.getroot()
        ns = {'svg': 'http://www.w3.org/2000/svg'}

        # Get positions of the instances of each glyph.
        glyph_positions = {}
        for use in root.findall('.//svg:use', ns):
            id = use.attrib['{http://www.w3.org/1999/xlink}href'][1:]
            x = float(use.attrib.get('x', 0))
            y = float(use.attrib.get('y', 0))

            if id not in glyph_positions:
                glyph_positions[id] = []
            glyph_positions[id].append((x, y))

        # Store positions in the Glyph objects
        for glyph in glyphs:
            glyph.positions = glyph_positions[glyph.id]
            for i in range(len(glyph.positions)):
                pos = glyph.positions[i]
                glyph.positions[i] = (pos[0], -pos[1])  # Invert y-coordinate

        return glyphs

    def __exit__(self, exc_type, exc_value, traceback):
        self.temp_dir.cleanup()


def create_glyph_curves(glyphs):
    for glyph in glyphs:
        n_segs = len(glyph.path)
        n_posi = len(glyph.positions)
        glyph.base_curves = [None] * n_segs
        glyph.instances = [[None] * n_segs] * n_posi

        # Create an Anima curve for each segment of the glyph.
        for j, seg in enumerate(glyph.path):
            start = seg.start
            end = seg.end
            p0 = (start.real, start.imag)
            p1 = (end.real, end.imag)

            if isinstance(seg, svgtools.Line):
                curve = Segment(p0, p1)
            elif isinstance(seg, svgtools.CubicBezier):
                ctrl1 = seg.control1
                ctrl2 = seg.control2
                c0 = (ctrl1.real, ctrl1.imag)
                c1 = (ctrl2.real, ctrl2.imag)
                curve = BezierCurve(p0, p1, control_pts=[c0, c1])
            else:
                raise ValueError(f"Unsupported segment type: {type(seg)}")

            # Store base curve for the current segment (located with respect to origin).
            curve.reflect((0, 1))
            glyph.base_curves[j] = curve

            # Create a copy and re-position the curve to the glyph's position.
            for i in range(n_posi):
                x, y = glyph.positions[i]
                crv = curve.copy()
                crv.translate(x, y)
                glyph.instances[i][j] = crv

            # Hide the base curve
            curve.hide()


def signed_area(points):
    # points: list of (x, y) tuples
    return 0.5 * sum(
        (x1 * y2 - x2 * y1)
        for (x1, y1), (x2, y2) in zip(points, points[1:] + [points[0]])
    )


def is_hole(points):
    return signed_area(points) < 0  # negative = clockwise = hole


def test_text_to_glyphs():
    # text = r'Lyy\\y'
    # text = 'T'
    # text = 'S'
    # text = 'Hello World!'
    # text = '$E = mc^2$'
    # text = r'boob\\y'
    # text = 'C'
    # text = '8'
    text = 'O'
    # text = 'Aghhhgg!!aaGH'
    with TeXtoSVG(text) as glyphs:
        create_glyph_curves(glyphs)

    for glyph in glyphs:
        curves = glyph.base_curves
        loops = [0]
        for j, curve in enumerate(curves):
            jnext = j + 1 if j < len(curves) - 1 else 0
            p0 = curve.point(1)
            p1 = curves[jnext].point(0)
            if (p1 - p0).length > 1e-13:
                loops.append(jnext)
                print('Hello')
        # for i, pos in enumerate(glyph.positions):
        #     curves = glyph.instances[i]
        #     for j, curve in enumerate(curves):
        #         pass

    # for curve in curves:
    #     if isinstance(curve, Segment):
    #         pass
    #     elif isinstance(curve, BezierCurve):
    #         pass
    #     else:
    #         raise ValueError(f"Unsupported curve type: {type(curve)}")
