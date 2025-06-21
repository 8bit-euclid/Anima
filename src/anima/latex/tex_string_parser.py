import re
from anima.diagnostics.logger import logger
from anima.latex.tex_object import TeXObject
from plasTeX.TeX import TeX
from pylatexenc.latexwalker import (
    LatexWalker,                          # Main walker class
    LatexEnvironmentNode as EnvironNode,  # \begin{env}...\end{env}
    LatexCharsNode as PlainTextNode,      # Plain text
    LatexGroupNode as GroupNode,          # {...} groups
    LatexMacroNode as CommandNode,        # \cmd{arg1}{arg2} or \cmd[opt]{arg}
    LatexMathNode as MathNode,            # $...$ and $$...$$
    LatexCommentNode as CommentNode,      # % comments
    LatexSpecialsNode as SpecialsNode     # Special characters like ~, &
)


SPACING_COMMANDS = {
    '!', ',', ':', ';', '>', '<', ' ',
    'quad', 'qquad', 'enspace', 'enskip',
    'hspace', 'vspace', 'hskip', 'vskip', 'kern', 'mkern', 'mskip',
    'smallskip', 'medskip', 'bigskip',
    'linebreak', 'newline', 'newpage', 'pagebreak',
    'phantom', 'hphantom', 'vphantom',
}

MAX_NODE_DEPTH = 7


def analyze_nodes(nodes, indent=0):
    assert indent < MAX_NODE_DEPTH, "Max node depth exceeded."
    jump = 2 * indent
    sep = '\n' + "-" * 10*(MAX_NODE_DEPTH - jump + 2)
    pad = '.' * jump

    for node in nodes:
        node_type = type(node).__name__
        def istype(t): return isinstance(node, t)
        range = f"[{node.pos}:{node.pos+node.len}]"

        print(f"{pad}Type: {node_type}")
        print(f"{pad}Range: {range}")
        print(f"{pad}Math mode?: {node.parsing_state.in_math_mode}")
        print(f"{pad}Verbatim: '{node.latex_verbatim()}'")
        # print(f"{pad}State: {node.parsing_state.s}")
        # # print(f"Context: {node.parsing_state.latex_context}")
        # print(f"Delimiter: {node.parsing_state.math_mode_delimiter}")

        # Plain Text: e.g. " i^2", "i=0", "_", ".\n", "^2)^2 + (pc)^2", etc.
        if istype(PlainTextNode):
            print(rf"{pad}Text: '{node.chars}'")

        # Command: e.g. \command{arg1}{arg2} or \command[opt]{arg}
        elif istype(CommandNode):
            print(rf"{pad}Command: '\{node.macroname}'")
            if node.nodeargd:
                args = node.nodeargd.argnlist
                print(rf"{pad}  Args: {len(args)}")
                for i, arg in enumerate(args):
                    print(rf"{pad}    Arg {i}: {arg}")
            print(rf"{pad}Post: '{node.macro_post_space}'")

        # Group: e.g. {...} or [...] groups
        elif istype(GroupNode):
            print(rf"{pad}Group with {len(node.nodelist)} inner nodes")
            print(sep)
            analyze_nodes(node.nodelist, indent=indent+1)  # Recursive analysis

        # Inline Math: $...$ or $$...$$.
        # Need to encapsulate with \begin{equation}...\end{equation} - see EnvironNode.
        elif istype(MathNode):
            math_type = "inline" if node.displaytype == "inline" else "display"
            print(rf"{pad}Math ({math_type})")
            print(sep)
            analyze_nodes(node.nodelist, indent=indent+1)  # Recursive analysis

        # Environment: e.g. \begin{env}...\end{env}.
        # Throw an error if the node has arguments
        elif istype(EnvironNode):
            print(rf"{pad}{range} Environment: {node.environmentname}")
            print(sep)
            if node.nodelist:
                analyze_nodes(node.nodelist, indent=indent+1)

        # Comments: e.g. % This is a comment
        # Ignore
        elif istype(CommentNode):
            print(rf"{pad}{range} Comment: '{node.comment}'")

        # Special Characters: e.g. ~, &, #, etc.
        elif istype(SpecialsNode):
            print(
                rf"{pad}{range} Special character: '{node.specials_chars}'")

        else:
            raise TypeError(f"Unknown node type: {node_type}")

        print(sep)


# Example usage
# latex = "abc"
# latex = r"\(i\pi = 0\)"
# latex = r'$e^{i\pi} + 1 = 0$'
# latex = r'$E^2 = (\mathit{mc}^2)^2 + (pc)^2$'
# latex = r'$E^2 = ({\mathit mc}^2)^2 + (pc)^2$'

latex = r"""
\begin{equation}
e^{i\pi} + 1 = 0 \\
0 = 0
\end{equation}
"""
latex = r"""
a
a
"""

# latex = r"""
# Einstein: $$E^2 = (\mathit{mc}^2)^2 + (pc)^2$$.
# Summation: $\sum_{i=0}^{\infty} i^2$.
# Special: a~b.
# """

# latex = r"""
# \section*{Introduction}

# This is \textbf{bold font} text with math: $E ^ 2 = (\mathit{mc} ^ 2) ^ 2 + (pc) ^ 2$.

# A fraction: $\frac{a}{b}$

# \begin{itemize}
# \item[1] First item
# \item[2] Second item with emph{emphasis}
# \end{itemize}

# Display math:
# $$\int_0 ^\infty e ^ {-x} dx = 1$$

# \begin{equation}
# \label{eq: example}
# a ^ 2 + b ^ 2 = c ^ 2

# % This is a comment
# \& % This is a special character(ampersand)

# \end{equation}
# """

walker = LatexWalker(latex)
nodes, a, b = walker.get_latex_nodes()
print("\nWalker Info:", len(nodes), a, b, '\n')
analyze_nodes(nodes)


latex = r"""
\section*{Introduction}

This is \textbf{bold font} text with math: $E ^ 2 = (\mathit{mc} ^ 2) ^ 2 + (pc) ^ 2$.

A fraction: $\frac{a}{b}$

\begin{itemize}
\item[1] First item
\item[2] Second item with \emph{emphasis}
\end{itemize}

Display math:
$$\int_0 ^\infty e ^ {-x} dx = 1$$

\begin{equation}
\label{eq: example}
a ^ 2 + b ^ 2 = c ^ 2
\end{equation}

% This is a comment
This is a special character(ampersand)
"""

# latex = r"{This {is}} \textbf{bold font} text. This is math: $E ^ 2 = (\mathit{mc} ^ 2)_2 + (pc) ^ 2$."
# latex = r"\(i\pi = 0\)"
# latex = r'$e^{i\pi} + 1 = 0$'
# latex = r'$E^2 = (\mathit{mc}^2)^2 + (pc)^2$'
# latex = r'$E^2 = ({\mathit mc}^2)^2 + (pc)^2$'


def walk_nodes(node, indent=0):
    pad = '..' * 2*indent
    print(f"{pad}{type(node).__name__}: '{getattr(node, 'source', '')}'")
    for child in getattr(node, 'childNodes', []):
        walk_nodes(child, indent+1)


tex = TeX()
tex.input(latex)

# for node in tex:
#     print(f"{type(node).__name__}: {getattr(node, 'source', '')}")

doc = tex.parse()
walk_nodes(doc)


class TeXObject(NamedTuple):
    """Simple TeX object representation."""
    text: str
    rendered: bool = True
    sub_objects: tuple = ()


class TeXStringParser:
    """Parser wrapped around the plasTeX Latex walker."""

    def __init__(self, text: str, math_mode: bool = False):
        """Initialize the TeX parser with regex patterns.
        Args:
            text (str): The LaTeX text to parse.
            math_mode (bool): Whether to enable math mode.
        """
        self._text = text
        self._nodes = LatexWalker(text)
        self._math_mode = math_mode
        self._pos = 0

    def parse(self) -> list[TeXObject]:
        """Parse TeX text using regex patterns."""
        if not self._text:
            return []

        objects = []

        return objects
