from anima.latex.tex_file_processor import TeXFileProcessor


def test_text_to_glyphs():
    # text = r'Lyy\\y'
    # text = 'T'
    # text = 'S'
    # text = 'Hello World!'
    # text = 'office'
    # text = '$E = mc^2$'
    text = r'$E^2 = (\mathit{mc}^2)^2 + (pc)^2$\textsuperscript{2}'
    # text = r'$E = \mathit{mc}^2$'
    # text = r'boob\\y'
    # text = 'C'
    # text = '8'
    # text = 'O{\Huge 8}'
    # text = 'O'
    # text = 'Aghhhgg!!aaGH'
    with TeXFileProcessor(text) as glyphs:
        for glyph in glyphs.values():
            glyph.create_curves()
            glyph.create_mesh()
            # glyph.create_instances()
