import os
from pathlib import Path

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
        self._document_class: str = None
        self._other_commands: list[str] = []
        self._packages: dict[str, str] = {}
        self._new_commands: dict[str, str] = {}
        self._body: list[str] = []
        if body:
            self.add_to_body(body)
        if font:
            self.set_main_font(font, font_size)

    def set_defaults(self):
        """Set default document class and font."""
        self.set_document_class("standalone", ["preview"]).set_main_font(DEFAULT_FONT, DEFAULT_FONT_SIZE).add_package(
            "amsmath"
        ).add_package("amssymb")
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

    def set_main_font(self, name: str, font_size: int | float = DEFAULT_FONT_SIZE):
        """Set the main font for the document. Adds the fontspec package if not already added.
        Optionally sets the default font size.
        Args:
            name: Name of the font package (e.g. 'Times New Roman', 'TeX Gyre Termes', etc.)
            font_size: Optional font size in points (e.g., 12)
        """
        if "fontspec" not in self._packages:
            self.add_package("fontspec")
        disable_ligatures = "Ligatures=NoCommon"
        self.add_to_preamble(rf"\setmainfont{{{name}}}[{disable_ligatures}]")
        self.add_to_preamble(rf"\fontsize{{{font_size}}}{{{1.2*float(font_size)}}}\selectfont")
        return self

    def add_package(self, name: str, options: str | list[str] | None = None):
        """Add a LaTeX package to the preamble.
        Args:
            name: Name of the package
            options: Package options
        """
        packages = self._packages
        assert name not in packages, f"Package '{name}' is already added."

        if options:
            options_str = get_options_str(options)
            packages[name] = rf"\usepackage[{options_str}]{{{name}}}"
        else:
            packages[name] = rf"\usepackage{{{name}}}"
        return self

    def add_new_command(self, name: str, definition: str):
        """Add a \\newcommand to the preamble.
        Args:
            name: Command name (with or without leading backslash)
            definition: Command definition
        """
        if not name.startswith("\\"):
            name = "\\" + name

        # Find all argument placeholders (#1, #2, etc.) if any exist
        import re

        args = re.findall(r"#(\d+)", definition)

        if not args:
            cmd = rf"\newcommand{{{name}}}{{{definition}}}"
        else:
            # Get the highest argument number
            num_args = max(int(arg) for arg in args)
            cmd = rf"\newcommand{{{name}}}[{num_args}]{{{definition}}}"

        self._new_commands[name] = cmd
        return self

    def add_to_preamble(self, entry: str):
        """Add a generic line to the preamble.
        Args:
            entry: Generic LaTeX entry to add
        """
        self._other_commands.append(entry)
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
            parts.append(rf"\fontsize{{{font_size}}}{{{1.2*font_size}}}\selectfont")
        if parts:
            text = f"{{{' '.join(parts)} {text}}}"
        self._body.append(text)
        return self

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
            if self._packages:
                parts.extend(list(self._packages.values()))
            if self._other_commands:
                parts.extend(self._other_commands)
            if self._new_commands:
                parts.extend(list(self._new_commands.values()))

            # Document body
            parts.append(r"\begin{document}")
            parts.extend(self._body)
            parts.append(r"\end{document}")

        return "\n".join(parts)

    def clear(self):
        """Clear all packages and commands."""
        self._document_class = None
        self._packages.clear()
        self._other_commands.clear()
        self._new_commands.clear()
        self._body.clear()
        return self

    def __str__(self) -> str:
        """Return the string representation of the LaTeX document.
        Returns:
            str: The LaTeX document as a string."""
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
