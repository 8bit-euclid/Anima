"""Unit tests for TeXStringParser class."""

import pytest

from anima.latex.tex_string_parser import SPACING_COMMANDS, TeXStringParser


class TestTeXStringParser:
    """Test suite for TeXStringParser functionality.

    The TeXStringParser uses plasTeX to parse LaTeX strings and returns
    a list of glyph strings (individual characters or TeX commands).
    """

    def test_parse_empty_string(self):
        """Test parsing an empty string returns empty list."""
        parser = TeXStringParser("")
        assert parser.parse() == []

    def test_parse_single_character(self):
        """Test parsing a single character."""
        parser = TeXStringParser("a")
        glyphs = parser.parse()
        assert glyphs == ["a"]

    def test_parse_simple_word(self):
        """Test parsing a simple word returns individual characters."""
        parser = TeXStringParser("abc")
        glyphs = parser.parse()
        assert glyphs == ["a", "b", "c"]

    def test_parse_multiple_words(self):
        """Test parsing multiple words (whitespace is skipped)."""
        parser = TeXStringParser("ab cd")
        glyphs = parser.parse()
        # Whitespace is skipped, so we get individual non-whitespace chars
        assert "a" in glyphs
        assert "b" in glyphs
        assert "c" in glyphs
        assert "d" in glyphs
        # Whitespace should not appear
        assert " " not in glyphs

    def test_parse_digits(self):
        """Test parsing digits."""
        parser = TeXStringParser("123")
        glyphs = parser.parse()
        assert glyphs == ["1", "2", "3"]

    def test_parse_punctuation(self):
        """Test parsing punctuation characters."""
        parser = TeXStringParser("a.b,c!")
        glyphs = parser.parse()
        assert "." in glyphs
        assert "," in glyphs
        assert "!" in glyphs

    def test_parse_math_mode_variable(self):
        """Test parsing a simple math mode expression."""
        parser = TeXStringParser("$x$")
        glyphs = parser.parse()
        assert "x" in glyphs

    def test_parse_greek_letter_command(self):
        """Test parsing Greek letter commands."""
        parser = TeXStringParser(r"$\alpha$")
        glyphs = parser.parse()
        assert r"\alpha" in glyphs

    def test_parse_multiple_greek_letters(self):
        """Test parsing multiple Greek letter commands."""
        parser = TeXStringParser(r"$\alpha\beta\gamma$")
        glyphs = parser.parse()
        assert r"\alpha" in glyphs
        assert r"\beta" in glyphs
        assert r"\gamma" in glyphs

    def test_parse_math_with_numbers(self):
        """Test parsing math with numbers."""
        parser = TeXStringParser(r"$x = 2$")
        glyphs = parser.parse()
        assert "x" in glyphs
        assert "=" in glyphs
        assert "2" in glyphs

    def test_parse_superscript(self):
        """Test parsing superscript expressions."""
        parser = TeXStringParser(r"$x^2$")
        glyphs = parser.parse()
        assert "x" in glyphs
        assert "2" in glyphs

    def test_parse_subscript(self):
        """Test parsing subscript expressions."""
        parser = TeXStringParser(r"$x_i$")
        glyphs = parser.parse()
        assert "x" in glyphs
        assert "i" in glyphs

    def test_spacing_commands_set_exists(self):
        """Test that SPACING_COMMANDS set contains expected commands."""
        assert "quad" in SPACING_COMMANDS
        assert "qquad" in SPACING_COMMANDS
        assert "!" in SPACING_COMMANDS
        assert "," in SPACING_COMMANDS
        assert " " in SPACING_COMMANDS

    def test_math_mode_flag(self):
        """Test that math_mode flag is stored correctly."""
        parser_no_math = TeXStringParser("x", math_mode=False)
        parser_math = TeXStringParser("x", math_mode=True)
        assert parser_no_math._math_mode is False
        assert parser_math._math_mode is True

    def test_text_property(self):
        """Test that text property is stored correctly."""
        text = r"Hello $x^2$ World"
        parser = TeXStringParser(text)
        assert parser._text == text

    def test_parse_fraction(self):
        """Test parsing fraction command."""
        parser = TeXStringParser(r"$\frac{1}{2}$")
        glyphs = parser.parse()
        # Fractions should parse to their component parts
        assert "1" in glyphs
        assert "2" in glyphs

    def test_parse_sqrt(self):
        """Test parsing square root command."""
        parser = TeXStringParser(r"$\sqrt{x}$")
        glyphs = parser.parse()
        # Should get the content of sqrt
        assert "x" in glyphs

    def test_parse_sum_command(self):
        """Test parsing sum command."""
        parser = TeXStringParser(r"$\sum$")
        glyphs = parser.parse()
        assert r"\sum" in glyphs

    def test_parse_integral_command(self):
        """Test parsing integral command."""
        parser = TeXStringParser(r"$\int$")
        glyphs = parser.parse()
        assert r"\int" in glyphs

    def test_parse_mixed_text_and_math(self):
        """Test parsing mixed text and math content."""
        parser = TeXStringParser(r"The value is $x$.")
        glyphs = parser.parse()
        # Should contain text characters and math
        assert "T" in glyphs
        assert "h" in glyphs
        assert "e" in glyphs
        assert "x" in glyphs
        assert "." in glyphs
