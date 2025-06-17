from anima.latex.tex_file_processor import TeXFileProcessor


def test_text_to_glyphs():
    # text = r'Lyy\\y'
    # text = 'T'
    # text = 'S'
    # text = 'Hello World!'
    # text = 'office'
    # text = r'$e^{i\pi} + 1 = 0$'
    # text = r'${e^{i\pi}} + 1 = \mathbf{0}$'
    # text = r"""a
    # a"""
    text = r"""
    \begin{align}
    e^{i\pi} + 1 = 0 \\
    0 = 0
    \end{align}
    """
    # text = '$E = mc^2$'
    # text = r'$E^2 = (\mathit{mc}^2)^2 + (pc)^2$'
    # text = r'$E = \mathit{mc}^2$'
    # text = 'C'
    # text = '8'
    # text = 'O{\Huge 8}'
    # text = 'O'
    with TeXFileProcessor(text) as glyphs:
        for _, glyph in glyphs.items():
            glyph.construct()
            # glyph.create_instances()
