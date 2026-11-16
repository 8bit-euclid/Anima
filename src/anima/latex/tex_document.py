from __future__ import annotations

from copy import deepcopy

DEFAULT_FONT = "TeX Gyre Termes"
DEFAULT_FONT_SIZE = 10  # Font size in points (LaTeX default is 10pt)


class TeXDocument:
    """A class representing a LaTeX document with a preamble and body.
    It allows setting document class, adding packages, defining new commands,
    and adding content to the document body. The document can be converted to a
    string representation suitable for LaTeX processing."""

    def __init__(
        self,
        body: str | None = None,
        font: str | None = None,
        font_size: int | float | None = None,
    ):
        self._document_class: str | None = None
        self._preamble: list[str] = []
        self._packages: set[str] = set()
        self._new_commands: set[str] = set()
        self._font_index: int | None = None
        self._body: list[str] = []
        if body:
            self.add_to_body(body)
        if font:
            self.set_main_font(font, DEFAULT_FONT_SIZE if font_size is None else font_size)

    def set_defaults(self) -> TeXDocument:
        """Set default document class and font."""
        self.set_document_class("standalone", ["preview"])
        self.add_package("fontspec").add_package("amsmath").add_package("amssymb")
        self.set_main_font(DEFAULT_FONT, DEFAULT_FONT_SIZE)
        return self

    def set_document_class(self, name: str, options: str | list[str] | None = None):
        """Set the document class in the preamble.

        Args:
            name: Name of the document class
            options: Class options
        """
        if options:
            options_str = get_options_str(options)
            self._document_class = rf"\documentclass[{options_str}]{{{name}}}"
        else:
            self._document_class = rf"\documentclass{{{name}}}"
        return self

    def set_main_font(self, name: str, font_size: int | float = DEFAULT_FONT_SIZE) -> TeXDocument:
        """Set the main font and default font size for the document.

        Adds fontspec if needed. Subsequent calls replace this method's previous
        font and size declarations in place.

        Args:
            name: Name of the font package (e.g. 'Times New Roman', 'TeX Gyre Termes', etc.)
            font_size: Optional font size in points (e.g., 12)
        """
        disable_ligatures = "Ligatures=NoCommon"
        commands = [
            rf"\setmainfont{{{name}}}[{disable_ligatures}]",
            rf"\fontsize{{{font_size}}}{{{1.2 * float(font_size)}}}\selectfont",
        ]
        if "fontspec" not in self._packages:
            self.add_package("fontspec")
        if self._font_index is None:
            self._font_index = len(self._preamble)
            self._preamble.extend(commands)
        else:
            self._preamble[self._font_index : self._font_index + len(commands)] = commands
        return self

    def add_package(self, name: str, options: str | list[str] | None = None) -> TeXDocument:
        """Add a LaTeX package to the preamble.

        Args:
            name: Name of the package
            options: Package options

        Raises:
            ValueError: If the package was already added through this method.
        """
        if name in self._packages:
            raise ValueError(f"Package '{name}' is already added.")

        if options:
            options_str = get_options_str(options)
            command = rf"\usepackage[{options_str}]{{{name}}}"
        else:
            command = rf"\usepackage{{{name}}}"
        self._packages.add(name)
        self._preamble.append(command)
        return self

    def add_new_command(self, name: str, definition: str) -> TeXDocument:
        """Add a \\newcommand to the preamble.

        Args:
            name: Command name (with or without leading backslash)
            definition: Command definition

        Raises:
            ValueError: If the command was already added through this method.
        """
        if not name.startswith("\\"):
            name = "\\" + name
        if name in self._new_commands:
            raise ValueError(f"Command '{name}' is already added.")

        # Find all argument placeholders (#1, #2, etc.) if any exist
        import re

        args = re.findall(r"#(\d+)", definition)

        if not args:
            cmd = rf"\newcommand{{{name}}}{{{definition}}}"
        else:
            # Get the highest argument number
            num_args = max(int(arg) for arg in args)
            cmd = rf"\newcommand{{{name}}}[{num_args}]{{{definition}}}"

        self._new_commands.add(name)
        self._preamble.append(cmd)
        return self

    def add_to_preamble(self, entry: str) -> TeXDocument:
        """Add a generic line to the preamble.

        Args:
            entry: Generic LaTeX entry to add
        """
        self._preamble.append(entry)
        return self

    def add_to_body(self, text: str, font: str | None = None, font_size: int | float | None = None):
        """Add text to the document body.

        Args:
            text: Text to add to the body. If it contains LaTeX commands, they will be processed as such.
            font: Optional font to use for this text. If None, DEFAULT_FONT is used.
            font_size: Optional font size in LaTeX points (11pt, 13.7pt, etc.). If None, DEFAULT_FONT_SIZE is used.
        """
        parts = []
        if font:
            parts.append(rf"\fontspec{{{font}}}")
        if font_size:
            parts.append(rf"\fontsize{{{font_size}}}{{{1.2 * font_size}}}\selectfont")
        if parts:
            text = f"{{{' '.join(parts)} {text}}}"
        self._body.append(text)
        return self

    def with_body(self, text: str, *, font_size: int | float | None = None) -> TeXDocument:
        """Create a document from this preamble-only template and the supplied body.

        The template is not modified and can be reused for other bodies.

        Args:
            text: LaTeX content for the new document.
            font_size: Optional base font size in TeX points.

        Returns:
            A separate document with the supplied body.

        Raises:
            ValueError: If this template already contains body content.
        """
        if self._body:
            raise ValueError("A TeX document template must not already contain body content.")
        document = deepcopy(self)
        document.add_to_body(text, font_size=font_size)
        return document

    def to_string(self, body_only: bool = False) -> str:
        """Return the string representation of the LaTeX document or its body.

        Args:
            body_only: If True, return only the document body without preamble.

        Raises:
            AssertionError: If the document class is not set or the document body is empty.

        Returns:
            str: The LaTeX document or its body as a string.
        """
        assert self._body, "The document body is empty."

        parts = []
        if body_only:
            # Only the body, no preamble
            parts.extend(self._body)
        else:
            # Document class
            assert self._document_class is not None, "The document class has not been set."
            parts.append(self._document_class)

            # Document preamble
            parts.extend(self._preamble)

            # Document body
            parts.append(r"\begin{document}")
            parts.extend(self._body)
            parts.append(r"\end{document}")

        return "\n".join(parts)

    def clear(self):
        """Clear all packages and commands."""
        self._document_class = None
        self._packages.clear()
        self._preamble.clear()
        self._new_commands.clear()
        self._font_index = None
        self._body.clear()
        return self

    def __str__(self) -> str:
        """Return the string representation of the LaTeX document.

        Returns:
            str: The LaTeX document as a string.
        """
        return self.to_string(body_only=False)


def get_options_str(options: str | list[str]) -> str:
    """Convert options to a string format for LaTeX.

    Args:
        options: Options as a string or a list of strings

    Returns:
        str: A comma-separated string of options, or a single string if not a list.

    Raises:
        AssertionError: If options are not specified.
    """
    assert options is not None, "Options have not been specified."
    return ", ".join(options) if isinstance(options, list) else str(options)
