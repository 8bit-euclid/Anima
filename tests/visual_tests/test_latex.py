from anima.latex.glyph_group import GlyphGroup


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

    GlyphGroup.from_tex_string(text)
