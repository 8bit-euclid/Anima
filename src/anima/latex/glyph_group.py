from __future__ import annotations

from anima.latex.glyph import Glyph
from anima.latex.glyph_body import MeshQuality
from anima.latex.tex_document import TeXDocument
from anima.latex.tex_document_processor import TeXDocumentProcessor
from anima.primitives.object import Object


class GlyphGroup(Object):
    """A group of glyphs that can be animated together as a single unit.

    Useful for representing words, equations, or other multi-glyph constructs.
    All glyphs in the group are added as children, enabling hierarchical
    animation and transformation.

    Attributes:
        glyphs: List of Glyph objects in this group.
    """

    def __init__(self, glyphs: list[Glyph] = None, name: str = "GlyphGroup"):
        """Initialize a GlyphGroup.

        Args:
            glyphs: Optional initial list of glyphs to add.
            name: Name for this group.
        """
        super().__init__(name=name)
        self._glyphs: list[Glyph] = []

        if glyphs:
            for glyph in glyphs:
                self.add_glyph(glyph)

    @classmethod
    def from_tex_string(
        cls,
        text: str,
        name: str = "GlyphGroup",
        mesh_quality: MeshQuality | None = None,
    ) -> GlyphGroup:
        """Create a GlyphGroup from a LaTeX string, with glyphs correctly positioned.

        Compiles the LaTeX string to SVG via dvisvgm, extracts glyph paths and
        typographic positions, and constructs a Glyph for each character instance
        placed at its correct location in Blender space. Names use rendered order
        and label characters, private-use font glyphs, and standalone shapes.

        Args:
            text: A LaTeX string (plain text or math mode).
            name: Name for the resulting GlyphGroup object.
            mesh_quality: Triangulation density/quality applied to every glyph
                body in the group. Defaults to MeshQuality.minimal().

        Returns:
            A GlyphGroup containing all positioned Glyph instances.
        """

        content = TeXDocument().set_defaults().add_to_body(text)
        group = cls(name=name)

        with TeXDocumentProcessor(content) as (glyph_paths, positions):
            for index, (gid, (x, y), char, shape_label) in enumerate(positions, start=1):
                glyph_name = _format_glyph_name(index, char, len(positions), shape_label)
                glyph = Glyph(glyph_paths[gid], name=glyph_name, mesh_quality=mesh_quality)
                glyph.text = char or ""
                glyph.location = (x, y, 0)
                group.add_glyph(glyph)

        return group

    def add_glyph(self, glyph: Glyph):
        """Add a glyph to this group.

        Args:
            glyph: The Glyph to add.

        Raises:
            TypeError: If the argument is not a Glyph instance.
        """
        if not isinstance(glyph, Glyph):
            raise TypeError(f"Expected Glyph instance, got {type(glyph).__name__}")
        self._glyphs.append(glyph)
        self.add_child(glyph)

    @property
    def glyphs(self) -> list[Glyph]:
        """Get the list of glyphs in this group.

        Returns:
            List of Glyph objects.
        """
        return self._glyphs

    @property
    def text(self) -> str:
        """Get the combined text of all glyphs.

        Returns:
            Concatenated text from all glyphs in order.
        """
        return "".join(g.text for g in self._glyphs)

    def __len__(self) -> int:
        """Get the number of glyphs in this group.

        Returns:
            Number of glyphs.
        """
        return len(self._glyphs)

    def __iter__(self):
        """Iterate over glyphs in this group.

        Yields:
            Each Glyph in order.
        """
        return iter(self._glyphs)

    def __getitem__(self, index: int) -> Glyph:
        """Get a glyph by index.

        Args:
            index: Index of the glyph.

        Returns:
            The Glyph at the given index.
        """
        return self._glyphs[index]


def _format_glyph_name(index: int, character: str | None, glyph_count: int, shape_label: str | None = None) -> str:
    """Format a sequential glyph name with a readable character or descriptive label.

    Args:
        index: The 1-based position of the glyph in rendered order.
        character: The character represented by the glyph, if available.
        glyph_count: The number of glyphs in the group, used to size the index.
        shape_label: Optional font glyph name or non-character shape label.

    Returns:
        A formatted glyph name string.
    """
    if shape_label is not None:
        label = shape_label
    elif character is None:
        label = "U+?"
    elif len(character) == 1 and character.isprintable() and not character.isspace():
        label = character
    else:
        label = "+".join(f"U+{ord(codepoint):04X}" for codepoint in character)
    index_width = max(2, len(str(glyph_count)))
    return f"{index:0{index_width}d}-{label}"
