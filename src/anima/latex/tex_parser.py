from anima.latex.tex_object import TeXObject
from pylatexenc.latexwalker import (
    LatexWalker,           # Main walker class
    LatexEnvironmentNode,  # \begin{env}...\end{env}
    LatexCharsNode,        # Plain text
    LatexGroupNode,        # {...} groups
    LatexMacroNode,        # \commands
    LatexMathNode,         # $...$ and $$...$$
    LatexCommentNode,      # % comments
    LatexSpecialsNode      # Special characters like ~, &
)


SPACING_COMMANDS = {
    '!', ',', ':', ';', '>', '<', ' ',
    'quad', 'qquad', 'enspace', 'enskip',
    'hspace', 'vspace', 'hskip', 'vskip', 'kern', 'mkern', 'mskip',
    'smallskip', 'medskip', 'bigskip',
    'linebreak', 'newline', 'newpage', 'pagebreak',
    'phantom', 'hphantom', 'vphantom',
}


def _node_to_texobject(node, math_mode=False):
    # Convert pylatexenc node to TeXObject recursively
    if isinstance(node, LatexCharsNode):
        return TeXObject(text=node.chars)
    elif isinstance(node, LatexGroupNode):
        sub_objs = tuple(_node_to_texobject(n, math_mode)
                         for n in node.nodelist)
        return TeXObject(
            text=node.latex_verbatim(),
            sub_objects=sub_objs
        )
    elif isinstance(node, LatexMacroNode):
        should_render = node.macroname not in SPACING_COMMANDS
        args_text = ""
        sub_objs = []
        for arg in node.nodeargd.argnlist:
            if arg is not None:
                args_text += arg.latex_verbatim()
                if should_render:
                    sub_objs.extend([_node_to_texobject(arg, math_mode)])
        return TeXObject(
            text=node.latex_verbatim(),
            rendered=should_render,
            sub_objects=tuple(sub_objs)
        )
    elif isinstance(node, LatexEnvironmentNode):
        sub_objs = tuple(_node_to_texobject(n, math_mode)
                         for n in node.nodelist)
        return TeXObject(
            text=node.latex_verbatim(),
            sub_objects=sub_objs
        )
    elif isinstance(node, LatexMathNode):
        sub_objs = tuple(_node_to_texobject(n, True) for n in node.nodelist)
        return TeXObject(
            text=node.latex_verbatim(),
            sub_objects=sub_objs
        )
    # fallback for unknown node types
    return TeXObject(text=node.latex_verbatim())


class TeXParser:
    """
    TeX parser using pylatexenc for extracting TeX commands, math environments, and text.
    Parses input strings into TeXObject trees.
    """

    def parse(self, text: str, math_mode: bool = False) -> list[TeXObject]:
        if not text:
            return []
        walker = LatexWalker(text)
        nodes, _, _ = walker.get_latex_nodes(pos=0)
        return [_node_to_texobject(node, math_mode) for node in nodes]


# Simple interface
def parse_tex(text: str) -> list[TeXObject]:
    """Parse TeX string into objects."""
    return TeXParser().parse(text)


def tex_to_text(objects: list[TeXObject]) -> str:
    """Convert to rendered text."""
    return ''.join(obj.text for obj in objects if obj.rendered)

#
#
#
#


def analyze_nodes(nodes):
    sep = '\n' + "-" * 40

    for node in nodes:
        if isinstance(node, LatexCharsNode):
            print(rf"Text: '{node.chars}'")

        elif isinstance(node, LatexMacroNode):
            print(rf"Command: \{node.macroname}")
            if node.nodeargd:
                print(rf"  Arguments: {len(node.nodeargd.argnlist)}")
                for i, arg in enumerate(node.nodeargd.argnlist):
                    print(rf"    Arg {i}: {arg}")
                    # if arg is not None:
                    #     print(f"    Arg {i}: {arg}")

        elif isinstance(node, LatexGroupNode):
            print(rf"Group with {len(node.nodelist)} inner nodes")
            analyze_nodes(node.nodelist)  # Recursive analysis

        elif isinstance(node, LatexMathNode):
            math_type = "inline" if node.displaytype == "inline" else "display"
            print(rf"Math ({math_type}): {node.nodelist}")

        elif isinstance(node, LatexEnvironmentNode):
            print(rf"Environment: {node.environmentname}")
            if node.nodelist:
                analyze_nodes(node.nodelist)
        else:
            print(rf"Unknown node type: {type(node).__name__}")

        print(sep)


# Example usage
latex = r"""
\section*{Introduction}
This is \textbf{bold font} text with math: $E = mc^2$.

\begin{itemize}
\item First item
\item Second item with \emph{emphasis}
\end{itemize}

Display math:
$$\int_0^\infty e^{-x} dx = 1$$
"""

walker = LatexWalker(latex)
nodes, a, b = walker.get_latex_nodes()
print("Values:", a, b)
analyze_nodes(nodes)
