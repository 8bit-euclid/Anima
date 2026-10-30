from anima.latex.glyph_body import MeshQuality
from anima.latex.glyph_group import GlyphGroup


def test_text_to_glyphs():
    """Build a visual gallery for text glyphs and common LaTeX math shapes."""
    # text = r"""
    # \section*{Introduction}

    # This is \textbf{bold font} text with math: $E ^ 2 = (\mathit{mc} ^ 2) ^ 2 + (pc) ^ 2$.

    # A fraction: $\frac{a}{b}$

    # \begin{itemize}
    # \item[1] First item
    # \item[2] Second item with \emph{emphasis}
    # \end{itemize}

    # Display math:
    # $$\int_0 ^\infty e ^ {-x} dx = 1$$

    # \begin{equation}
    # \label{eq: example}
    # a ^ 2 + b ^ 2 = c ^ 2
    # \end{equation}
    # """

    # text = r'Lyy\\y'
    # text = 'T'
    # text = 'S'
    # text = 'Hello World!'
    # text = 'office'
    # text = r'$e^{i\pi} + 1 = 0$'
    # text = r'${e^{i\pi}} + 1 = \mathbf{0}$'
    # text = r"""\'e
    #
    #     a"""
    # text = r"""
    # \begin{align}
    # e^{i\pi} + 1 = 0 \\
    # 0 = 0
    # \end{align}
    # """
    # text = '$E = mc^2$'
    # text = r"$E^2 = (\mathit{mc}^2)^2 + (pc)^2$"
    # text = r'$E = \mathit{mc}^2$'
    # text = 'C'
    # text = "B"
    text = "o08AaB"  # Test glyphs with holes
    # text = 'O{\Huge 8}'
    # text = "O"
    # text = "O8P"
    # text = "8"
    # text = "P"
    # text = r'$s = ut + \frac{1}{2}at^2$'
    # text = r'$\frac{x^2 - 1}{x^2 + 1}$'

    # Default minimal quality: turning-angle-adaptive boundary, no interior points.
    GlyphGroup.from_tex_string(text, mesh_quality=MeshQuality.high())

    samples = (
        ("PlainText", "Anima 012: AaBbOo"),
        ("Radical", r"$\sqrt{x^2+y^2}$"),
        ("Fractions", r"$\frac{1}{2}+\frac{x^2-1}{x^2+1}$"),
        ("Operators", r"$\sum_{i=1}^{n} x_i+\int_0^1 f(x)\,dx$"),
        ("AccentsDelimiters", r"$\left(\frac{a}{b}\right)+\hat{x}+\vec{y}$"),
    )
    row_spacing = 16

    for row, (sample_name, text) in enumerate(samples):
        group = GlyphGroup.from_tex_string(
            text,
            name=f"Latex_{sample_name}",
            mesh_quality=MeshQuality.high(),
        )
        group.location = (0, -row * row_spacing, 0)
