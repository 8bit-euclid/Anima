from anima.latex.tex_document_processor import TeXDocumentProcessor
from anima.latex.tex_document import TeXDocument
from anima.latex.glyph import Glyph


def test_text_to_glyphs():
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
    # text = r'$E^2 = (\mathit{mc}^2)^2 + (pc)^2$'
    # text = r'$E = \mathit{mc}^2$'
    # text = 'C'
    # text = '8'
    # text = 'O{\Huge 8}'
    # text = 'O'

    # Use provided latex document or setup a default one
    if isinstance(text, str):
        content = TeXDocument().set_defaults().add_to_body(text)

    with TeXDocumentProcessor(content) as glyph_data:
        glyph_paths, positions = glyph_data
        for _, path in glyph_paths.items():
            glyph = Glyph(path)

    print(*positions, sep='\n')
