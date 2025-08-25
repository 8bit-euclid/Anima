import re

from plasTeX.TeX import TeX

from anima.diagnostics import format_output, logger
from anima.latex.tex_object import TeXObject

SPACING_COMMANDS = {
    "!",
    ",",
    ":",
    ";",
    ">",
    "<",
    " ",
    "quad",
    "qquad",
    "enspace",
    "enskip",
    "hspace",
    "vspace",
    "hskip",
    "vskip",
    "kern",
    "mkern",
    "mskip",
    "smallskip",
    "medskip",
    "bigskip",
    "linebreak",
    "newline",
    "newpage",
    "pagebreak",
    "phantom",
    "hphantom",
    "vphantom",
}


class TeXStringParser:
    """Parser wrapped around the plasTeX Latex node walker."""

    def __init__(self, text: str, math_mode: bool = False):
        """Initialize the TeX parser with regex patterns.
        Args:
            text (str): The LaTeX text to parse.
            math_mode (bool): Whether to enable math mode.
        """
        self._text = text
        self._math_mode = math_mode

    def parse(self) -> list[str]:
        """Parse TeX text using plasTeX and create a (glyph, latex_text) tuple for each glyph."""
        if not self._text:
            return []

        logger.info("Parsing TeX string...")
        logger.debug(format_output("TeX string content", self._text))

        tex = TeX()
        tex.input(self._text)
        doc = tex.parse()
        glyphs = []

        def walk_and_collect(node):
            # If node is a leaf node and has text, create a tuple (glyph, latex_text)
            child_nodes = getattr(node, "childNodes", [])
            if child_nodes:
                # Recursively process child nodes
                for child in child_nodes:
                    walk_and_collect(child)
            elif hasattr(node, "textContent"):
                assert hasattr(node, "source"), "Node must have a 'source' attribute for latex text"
                tex_src = node.source.strip()
                unicode = node.textContent.strip()
                if tex_src == "":  # skip whitespace
                    return

                if not tex_src.startswith("\\"):
                    assert unicode == tex_src, f"Expected unicode '{unicode}' to match TeX source '{tex_src}'"
                    for char in tex_src:
                        if char.strip():  # skip whitespace
                            glyphs.append(char)
                else:  # tex_src is a command
                    if node.attributes:
                        for attr in node.attributes.values():
                            walk_and_collect(attr)
                    else:
                        glyphs.append(tex_src)

        walk_and_collect(doc)

        logger.debug(format_output("Parsed glyphs", glyphs))

        return glyphs
