import re
from anima.diagnostics.logger import logger
from anima.latex.tex_object import TeXObject
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


def _node_to_texobject(node, math_mode=False):
    # Convert pylatexenc node to TeXObject recursively
    if isinstance(node, PlainTextNode):
        return TeXObject(text=node.chars)

    elif isinstance(node, GroupNode):
        sub_objs = tuple(_node_to_texobject(n, math_mode)
                         for n in node.nodelist)
        return TeXObject(
            text=node.latex_verbatim(),
            sub_objects=sub_objs
        )

    elif isinstance(node, CommandNode):
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

    elif isinstance(node, EnvironNode):
        sub_objs = tuple(_node_to_texobject(n, math_mode)
                         for n in node.nodelist)
        return TeXObject(
            text=node.latex_verbatim(),
            sub_objects=sub_objs
        )

    elif isinstance(node, MathNode):
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

        # Plain Text: e.g. ' i^2', 'i=0', '_', '.\n', '^2)^2 + (pc)^2', etc.
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


# class TeXObject(NamedTuple):
#     """Simple TeX object representation."""
#     text: str
#     rendered: bool = True
#     sub_objects: tuple = ()


class TeXParser:
    """Regex-based TeX parser"""

    # Spacing commands that don't render
    SPACING = {
        '!', ',', ':', '>', ';', ' ',  # char commands
        'quad', 'qquad', 'linebreak', 'dec', 'decc', 'deccc',
        'inc', 'incc', 'inccc', 'vdec', 'vdecc', 'vdeccc',
        'vinc', 'vincc', 'vinccc'
    }

    # Main parsing patterns
    PATTERNS = {
        'math_double': re.compile(r'\$\$(.*?)\$\$', re.DOTALL),
        'math_single': re.compile(r'\$(.*?)\$', re.DOTALL),
        'command': re.compile(r'\\([a-zA-Z]+|[^a-zA-Z])'),
        'braces': re.compile(r'\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}'),
        'scripts': re.compile(r'([_^])(\{[^{}]+\}|[^{}\s])'),
        'char': re.compile(r'[^\\${}^_]+')
    }

    def __init__(self, text: str, math_mode: bool = False):
        """Initialize the TeX parser with regex patterns.
        Args:
            text (str): The LaTeX text to parse.
            math_mode (bool): Whether to enable math mode.
        """
        self._nodes = LatexWalker(text)
        self._text = text
        self._math_mode = math_mode
        self._pos = 0

    def parse(self) -> list[TeXObject]:
        """Parse TeX text using regex patterns."""
        if not self._text:
            return []

        objects = []

        return objects

#     def _parse_math(self, text: str, pos: int, is_double: bool) -> tuple:
#         """Parse $...$ or $...$ math blocks."""
#         pattern = 'math_double' if is_double else 'math_single'
#         match = self.PATTERNS[pattern].match(text, pos)
#         if not match:
#             delim = '$' if is_double else '

#     def _parse_command(self, text: str, pos: int, math_mode: bool) -> tuple:
#         """Parse TeX commands like \\alpha or !."""
#         match = self.PATTERNS['command'].match(text, pos)
#         if not match:
#             raise ValueError("Invalid command")

#         cmd_name = match.group(1)
#         full_cmd = match.group(0)
#         should_render = cmd_name not in self.SPACING

#         # Check for arguments after command
#         args_start = match.end()
#         args_text = ""
#         sub_objects = []

#         # Parse braced arguments {arg1}{arg2}
#         brace_pos = args_start
#         while brace_pos < len(text) and text[brace_pos] == '{':
#             brace_match = self._find_matching_brace(text, brace_pos)
#             if not brace_match:
#                 break

#             arg_content = text[brace_pos + 1:brace_match]
#             args_text += text[brace_pos:brace_match + 1]

#             if should_render:
#                 sub_objects.extend(self.parse(arg_content, math_mode))

#             brace_pos = brace_match + 1

#         # Parse scripts ^{} or _{}
#         script_pos = brace_pos
#         if script_pos < len(text) and text[script_pos] in '^_':
#             scripts, script_text = self._parse_scripts(text, script_pos)
#             args_text += script_text
#             sub_objects.extend(scripts)
#             script_pos += len(script_text)

#         obj = TeXObject(
#             text=full_cmd + args_text,
#             rendered=should_render,
#             sub_objects=tuple(sub_objects)
#         )

#         return obj, max(match.end(), script_pos)

#     def _parse_text(self, text: str, pos: int, math_mode: bool) -> tuple:
#         """Parse regular text, handling scripts in math mode."""
#         if pos >= len(text):
#             return None, pos

#         # Single character
#         char = text[pos]
#         new_pos = pos + 1

#         # In math mode, check for trailing scripts
#         if math_mode and new_pos < len(text) and text[new_pos] in '^_':
#             scripts, script_text = self._parse_scripts(text, new_pos)
#             obj = TeXObject(
#                 text=char + script_text,
#                 sub_objects=tuple(scripts)
#             )
#             new_pos += len(script_text)
#         else:
#             obj = TeXObject(char)

#         return obj, new_pos

#     def _parse_scripts(self, text: str, pos: int) -> tuple:
#         """Parse ^ {} and _{} scripts."""
#         scripts = []
#         script_text = ""

#         # Parse up to 2 scripts (sub/super in any order)
#         for _ in range(2):
#             if pos >= len(text) or text[pos] not in '^_':
#                 break

#             script_char = text[pos]
#             script_text += script_char
#             pos += 1

#             if pos < len(text):
#                 if text[pos] == '{':
#                     # Braced script like ^{content}
#                     end_brace = self._find_matching_brace(text, pos)
#                     if end_brace:
#                         content = text[pos + 1:end_brace]
#                         script_text += text[pos:end_brace + 1]
#                         scripts.extend(self.parse(content, math_mode=True))
#                         pos = end_brace + 1
#                 else:
#                     # Single char script like ^2
#                     char = text[pos]
#                     script_text += char
#                     scripts.append(TeXObject(char))
#                     pos += 1

#         return scripts, script_text

#     def _find_matching_brace(self, text: str, start: int) -> int:
#         """Find matching closing brace."""
#         if text[start] != '{':
#             return None

#         depth = 0
#         for i in range(start, len(text)):
#             if text[i] == '{':
#                 depth += 1
#             elif text[i] == '}':
#                 depth -= 1
#                 if depth == 0:
#                     return i
#         return None
