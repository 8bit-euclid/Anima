from anima.latex.tex_document_processor import TeXDocumentProcessor
from anima.latex.tex_document import TeXDocument
from anima.latex.glyph import Glyph
from anima.latex.tex_string_parser import TeXStringParser


def test_text_to_glyphs():
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
    text = r"""\'e

    a"""
    # text = r"""
    # \begin{align}
    # e^{i\pi} + 1 = 0 \\
    # 0 = 0
    # \end{align}
    # """
    # text = '$E = mc^2$'
    text = r'$E^2 = (\mathit{mc}^2)^2 + (pc)^2$'
    # text = r'$E = \mathit{mc}^2$'
    # text = 'C'
    # text = '8'
    # text = 'O{\Huge 8}'
    # text = 'O'
    # text = r'$s = ut + \frac{1}{2}at^2$'
    # text = r'$\frac{x^2 - 1}{x^2 + 1}$'

    glyphs = TeXStringParser(text).parse()

    # Use provided latex document or setup a default one
    if isinstance(text, str):
        content = TeXDocument().set_defaults().add_to_body(text)

    with TeXDocumentProcessor(content) as glyph_data:
        glyph_paths, positions = glyph_data
        for _, path in glyph_paths.items():
            glyph = Glyph(path)

    # print(*positions, sep='\n')
