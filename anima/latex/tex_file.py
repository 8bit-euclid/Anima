DEFAULT_FONT = "TeX Gyre Termes"
DEFAULT_FONT_SIZE = 10  # Font size in points (LaTeX default is 10pt)


class TeXFile:
    def __init__(self):
        self._document_class: str = None
        self._lines: list[str] = []
        self._packages: dict[str, str] = {}
        self._new_commands: dict[str, str] = {}
        self._text: list[str] = []

    def set_defaults(self):
        """Set default document class and font."""
        return self.set_document_class('standalone', ['preview'])\
                   .set_main_font(DEFAULT_FONT)

    def set_document_class(self, name: str, options: str | list[str] | None = None):
        """Set the document class in the preamble.

        Args:
            name: Name of the document class
            options: Class options
        """
        if options:
            options_str = get_options_str(options)
            self._document_class = rf'\documentclass[{options_str}]{{{name}}}'
        else:
            self._document_class = rf'\documentclass{{{name}}}'
        return self

    def set_main_font(self, name: str):
        """Set the main font for the document. Assumes that the fonstspec package is used.

        Args:
            name: Name of the font package (e.g. 'Times New Roman', 'TeX Gyre Termes', etc.)
            options: Font options
        """
        if 'fontspec' not in self._packages:
            self.add_package('fontspec')
        return self.add_to_preamble(fr'\setmainfont{{{name}}}')

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
            packages[name] = rf'\usepackage[{options_str}]{{{name}}}'
        else:
            packages[name] = rf'\usepackage{{{name}}}'
        return self

    def add_new_command(self, name: str, definition: str):
        """Add a \\newcommand to the preamble.

        Args:
            name: Command name (with or without leading backslash)
            definition: Command definition
        """
        import re

        if not name.startswith('\\'):
            name = '\\' + name

        # Find all argument placeholders (#1, #2, etc.) if any exist
        args = re.findall(r'#(\d+)', definition)

        if not args:
            cmd = rf'\newcommand{{{name}}}{{{definition}}}'
        else:
            # Get the highest argument number
            num_args = max(int(arg) for arg in args)
            cmd = rf'\newcommand{{{name}}}[{num_args}]{{{definition}}}'

        self._new_commands[name] = cmd
        return self

    def add_to_preamble(self, line: str):
        """Add a generic line to the preamble.

        Args:
            line: Generic LaTeX line to add
        """
        self._lines.append(line)
        return self

    def add_text(self, text: str, font: str | None = None, font_size: int | float | None = None):
        """Add text to the document body.

        Args:
            text: Text to add
            font: Optional font to use for this text
            font_size: Optional font size in LaTeX points (11pt, 13.7pt, etc.)
        """
        parts = []
        if font:
            parts.append(rf'\fontspec{{{font}}}')
        if font_size:
            parts.append(
                rf'\fontsize{{{font_size}}}{{{1.2*font_size}}}\selectfont')
        if parts:
            text = f"{{{' '.join(parts)} {text}}}"
        self._text.append(text)
        return self

    def clear(self):
        """Clear all packages and commands."""
        self._document_class = None
        self._packages.clear()
        self._lines.clear()
        self._new_commands.clear()
        return self

    def __str__(self):
        """Return the string representation of the document."""
        assert self._document_class is not None, "The document class has not been set."
        assert self._text, "The document body is empty."

        # Document preamble
        parts = [self._document_class]
        if self._packages:
            parts.extend(list(self._packages.values()))
        if self._lines:
            parts.extend(self._lines)
        if self._new_commands:
            parts.extend(list(self._new_commands.values()))

        # Document body
        parts.append(r'\begin{document}')
        parts.extend(self._text)
        parts.append(r'\end{document}')

        return '\n'.join(parts)


def get_options_str(options: str | list[str]):
    """Convert options to a string format for LaTeX.
    Args:
        options: Options as a string or a list of strings
    """
    assert options is not None, "Options have not been specified."
    return ', '.join(options) if isinstance(options, list) else str(options)
