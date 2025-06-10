import os
from pathlib import Path


DEFAULT_FONT = 'TeX Gyre Termes'
DEFAULT_FONT_SIZE = 10  # Font size in points (LaTeX default is 10pt)
GLYPH_MAP_MODULE = 'glyph_mapping'  # Lua file for glyph mapping


class TeXFile:
    def __init__(self):
        self._document_class: str = None
        self._other_commands: list[str] = []
        self._packages: dict[str, str] = {}
        self._new_commands: dict[str, str] = {}
        self._text: list[str] = []

    def set_defaults(self):
        """Set default document class and font."""
        self.set_document_class('standalone', ['preview'])\
            .set_main_font(DEFAULT_FONT)\
            .add_package('amsmath')\
            .add_package('amssymb')\
            .configure_lua_shipout()
        return self

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
        """Set the main font for the document. Adds the fonstspec package if not already added. Note that ligatures are disabled by default.

        Args:
            name: Name of the font package (e.g. 'Times New Roman', 'TeX Gyre Termes', etc.)
            options: Font options
        """
        if 'fontspec' not in self._packages:
            self.add_package('fontspec')
        disable_ligatures = 'Ligatures=NoCommon'
        return self.add_to_preamble(fr'\setmainfont{{{name}}}[{disable_ligatures}]')

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
        if not name.startswith('\\'):
            name = '\\' + name

        # Find all argument placeholders (#1, #2, etc.) if any exist
        import re
        args = re.findall(r'#(\d+)', definition)

        if not args:
            cmd = rf'\newcommand{{{name}}}{{{definition}}}'
        else:
            # Get the highest argument number
            num_args = max(int(arg) for arg in args)
            cmd = rf'\newcommand{{{name}}}[{num_args}]{{{definition}}}'

        self._new_commands[name] = cmd
        return self

    def add_to_preamble(self, entry: str):
        """Add a generic line to the preamble.

        Args:
            entry: Generic LaTeX entry to add
        """
        self._other_commands.append(entry)
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

    def configure_lua_shipout(self):
        """Add necessary packages and setup lua commands for shipout of character-glyph mapping metadata during TeX->DVI compilation."""
        ensure_lua_script_exists()
        self.add_package('luacode')\
            .add_to_preamble(rf"\directlua{{require('{GLYPH_MAP_MODULE}')}}")\
            .add_to_preamble(rf"\AddToHook{{shipout/before}}{{\directlua{{{GLYPH_MAP_MODULE}.shipout()}}}}")
        return self

    def clear(self):
        """Clear all packages and commands."""
        self._document_class = None
        self._packages.clear()
        self._other_commands.clear()
        self._new_commands.clear()
        self._text.clear()
        return self

    def to_string(self):
        """Return the string representation of the LaTeX document.
        Raises:
            AssertionError: If the document class is not set or the document body is empty.
        Returns:
            str: The LaTeX document as a string.
        """
        assert self._document_class is not None, "The document class has not been set."
        assert self._text, "The document body is empty."

        parts = [self._document_class]

        # Document preamble
        if self._packages:
            parts.extend(list(self._packages.values()))
        if self._other_commands:
            parts.extend(self._other_commands)
        if self._new_commands:
            parts.extend(list(self._new_commands.values()))

        # Document body
        parts.append(r'\begin{document}')
        parts.extend(self._text)
        parts.append(r'\end{document}')

        return '\n'.join(parts)

    def __str__(self):
        """Return the string representation of the LaTeX document.
        Returns:
            str: The LaTeX document as a string."""
        return self.to_string()


def ensure_lua_script_exists():
    """Ensure that the glyph mapping Lua file exists in the project root.
    Raises:
        AssertionError: If the glyph mapping Lua file does not exist.
    """
    # Get absolute path of current script's directory
    curr_dir = os.path.dirname(os.path.abspath(__file__))
    lua_file = Path(curr_dir)/f'scripts/{GLYPH_MAP_MODULE}.lua'
    assert lua_file.exists(), \
        f"Glyph mapping Lua file '{lua_file}' does not exist."


def get_options_str(options: str | list[str]):
    """Convert options to a string format for LaTeX.
    Args:
        options: Options as a string or a list of strings
    """
    assert options is not None, "Options have not been specified."
    return ', '.join(options) if isinstance(options, list) else str(options)
