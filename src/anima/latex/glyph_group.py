from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping, Sequence
from math import isfinite
from typing import TYPE_CHECKING, cast, overload

import svgpathtools as svgtools

from anima.latex.glyph import Glyph, glyph_write_on
from anima.latex.glyph_body import MeshQuality
from anima.latex.tex_doc_processor import TeXDocumentProcessor, TeXPartMappingError, _part_preamble
from anima.latex.tex_document import TeXDocument
from anima.primitives.group import Group
from anima.primitives.object import Object
from anima.scene.state import get_profile

if TYPE_CHECKING:
    from anima.animation.effects import Effect, Stagger
    from anima.animation.stagger import Ordering

# dvisvgm's coordinates are in big points (1/72 inch); TeX points are 1/72.27 inch.
_TEX_POINT_IN_SVG_UNITS = 72 / 72.27


class GlyphSelection(Sequence[Glyph]):
    """A read-only snapshot of glyph references that does not change their parents."""

    def __init__(self, glyphs: Iterable[Glyph] = ()) -> None:
        self._glyphs = tuple(glyphs)

    def __len__(self) -> int:
        return len(self._glyphs)

    @overload
    def __getitem__(self, index: int) -> Glyph: ...

    @overload
    def __getitem__(self, index: slice) -> GlyphSelection: ...

    def __getitem__(self, index: int | slice) -> Glyph | GlyphSelection:
        if isinstance(index, slice):
            return GlyphSelection(self._glyphs[index])
        return self._glyphs[index]

    @property
    def text(self) -> str:
        """Return the concatenated rendered text of the selected glyphs."""
        return "".join(glyph.text for glyph in self._glyphs)


class GlyphGroup(Group):
    """A `Group` that holds only glyphs, in order, and can be animated as a single unit.

    Useful for representing words, equations, or other multi-glyph constructs. Glyphs are the group's
    children, so the group's children are the single source of truth; every way of adding a child
    (`add` and `add_children`) rejects anything that is not a `Glyph`.
    """

    def __init__(
        self,
        glyphs: Iterable[Glyph] = (),
        *,
        name: str = "GlyphGroup",
        parent: Object | None = None,
    ) -> None:
        """Initialize a GlyphGroup.

        Args:
            glyphs: Glyphs to add as children, in order.
            name: Name for this group.
            parent: The parent object. Defaults to None.

        Raises:
            TypeError: If any of the glyphs is not a Glyph instance.
        """
        super().__init__(glyphs, name=name, parent=parent)
        self._parts: dict[str, tuple[Glyph, ...]] = {}

    def add_child(self, object: Object) -> None:
        """Add a glyph as a child of this group.

        Args:
            object: The Glyph to add.

        Raises:
            TypeError: If the argument is not a Glyph instance.
            ValueError: If the glyph already belongs to another parent.
        """
        if not isinstance(object, Glyph):
            raise TypeError(f"Expected Glyph instance, got {type(object).__name__}")
        super().add_child(object)

    @classmethod
    def from_tex_string(
        cls,
        text: str,
        name: str = "GlyphGroup",
        mesh_quality: MeshQuality | None = None,
        *,
        font_size: float | None = None,
        with_borders: bool = False,
        tex_template: TeXDocument | None = None,
    ) -> GlyphGroup:
        """Create a GlyphGroup from a LaTeX string, with glyphs correctly positioned.

        Compiles the LaTeX string to SVG via dvisvgm, extracts glyph outlines and
        typographic positions, and constructs a Glyph for each character instance
        placed at its correct location in Blender space. Names use rendered order
        and label characters, private-use font glyphs, and standalone shapes.

        Args:
            text: A LaTeX string (plain text or math mode).
            name: Name for the resulting GlyphGroup object.
            mesh_quality: Triangulation density/quality applied to every glyph
                body in the group. Defaults to MeshQuality.minimal().
            font_size: Base font size in TeX points. Defaults to the profile's body size.
                LaTeX sizing commands in text can override this size.
            with_borders: Whether to create animatable outlines for each glyph. Defaults to False.
            tex_template: Preamble-only TeX document to use without modifying it. Defaults to Anima's
                standalone document with TeX Gyre Termes, amsmath, and amssymb.

        Returns:
            A GlyphGroup containing all positioned Glyph instances.

        Raises:
            ValueError: If font_size is not finite and positive or the template already has body content.
        """
        return cls._from_tex(
            text, name, mesh_quality, font_size=font_size, with_borders=with_borders, tex_template=tex_template
        )

    @classmethod
    def from_tex_parts(
        cls,
        parts: Mapping[str, str],
        name: str = "GlyphGroup",
        mesh_quality: MeshQuality | None = None,
        *,
        font_size: float | None = None,
        with_borders: bool = False,
        tex_template: TeXDocument | None = None,
    ) -> GlyphGroup:
        """Typeset ordered, named TeX fragments together and record their glyphs.

        Fragments are concatenated without separators. Each fragment must have
        balanced braces and must not end with a control sequence. Boundaries
        must not split TeX arguments, comments, verbatim content, or macro
        definitions.

        Args:
            parts: Nonempty mapping of unique names to contiguous TeX fragments.
            name: Name for the resulting group.
            mesh_quality: Triangulation quality for glyph bodies.
            font_size: Base font size in TeX points.
            with_borders: Whether to create animatable glyph outlines.
            tex_template: Optional reusable preamble-only TeX document.

        Raises:
            ValueError: If parts is empty, a name is empty, the font size is invalid,
                or the template already has body content.
            TypeError: If a name or fragment is not a string.
            TeXPartMappingError: If SVG output cannot be reliably mapped to the parts.
        """
        entries = tuple(parts.items())
        if not entries:
            raise ValueError("parts must not be empty.")
        if any(not isinstance(key, str) or not isinstance(fragment, str) for key, fragment in entries):
            raise TypeError("Part names and fragments must be strings.")
        if any(not key for key, _ in entries):
            raise ValueError("Part names must not be empty.")
        for key, fragment in entries:
            _validate_part_fragment(key, fragment)
        text = (
            "".join(
                rf"\global\AnimaSemanticPartAttribute={index}\relax\directlua{{anima_semantic_boundary({index})}}"
                + fragment
                for index, (_, fragment) in enumerate(entries)
            )
            + r"\global\AnimaSemanticPartAttribute=-1\relax"
        )
        return cls._from_tex(
            text,
            name,
            mesh_quality,
            font_size=font_size,
            with_borders=with_borders,
            tex_template=tex_template,
            part_names=tuple(key for key, _ in entries),
        )

    @classmethod
    def _from_tex(
        cls,
        text: str,
        name: str,
        mesh_quality: MeshQuality | None,
        *,
        font_size: float | None,
        with_borders: bool,
        tex_template: TeXDocument | None,
        part_names: tuple[str, ...] | None = None,
    ) -> GlyphGroup:
        profile = get_profile()
        if font_size is None:
            font_size = profile.body_font_size
        if not isfinite(font_size) or font_size <= 0:
            raise ValueError("font_size must be finite and positive.")
        svg_scale = profile.tex_point_size / _TEX_POINT_IN_SVG_UNITS
        template = TeXDocument().set_defaults() if tex_template is None else tex_template
        content = template.with_body(text, font_size=font_size)
        if part_names is not None:
            content.add_to_preamble(_part_preamble(len(part_names)))

        processor = (
            TeXDocumentProcessor(content)
            if part_names is None
            else TeXDocumentProcessor(content, part_names=part_names)
        )
        with processor as (glyph_outlines, positions):
            group = cls(name=name)
            for index, (gid, (x, y), char, shape_label) in enumerate(positions, start=1):
                glyph_name = _format_glyph_name(index, char, len(positions), shape_label)
                glyph = Glyph(
                    _scale_outline(glyph_outlines[gid], svg_scale),
                    name=glyph_name,
                    mesh_quality=mesh_quality,
                    with_border=with_borders,
                )
                glyph.text = char or ""
                glyph.location = (x * svg_scale, y * svg_scale, 0)
                group.add(glyph)

        if part_names is not None:
            if processor.part_indices is None:
                raise RuntimeError("The TeX processor did not return part mappings.")
            glyphs = group.glyphs
            group._parts = {
                name: tuple(glyphs[index] for index in indices) for name, indices in processor.part_indices.items()
            }
        return group

    @property
    def part_names(self) -> tuple[str, ...]:
        """Return the names of explicitly supplied TeX parts in input order."""
        return tuple(self._parts)

    def part(self, name: str) -> GlyphSelection:
        """Return a non-owning snapshot of the glyphs rendered for a named part.

        Raises:
            KeyError: If no part has the given name.
        """
        return GlyphSelection(self._parts[name])

    @property
    def glyphs(self) -> list[Glyph]:
        """Get the glyphs in this group.

        Returns:
            A new list of the group's children, in order. `add_child()` guarantees that all of them are glyphs.
        """
        return cast("list[Glyph]", list(self._children))

    @property
    def text(self) -> str:
        """Get the combined text of all glyphs.

        Returns:
            Concatenated text from all glyphs in order.
        """
        return "".join(g.text for g in self.glyphs)

    def __len__(self) -> int:
        """Get the number of glyphs in this group.

        Returns:
            Number of glyphs.
        """
        return len(self._children)

    def __iter__(self) -> Iterator[Glyph]:
        """Iterate over glyphs in this group.

        Yields:
            Each Glyph in order.
        """
        return iter(self.glyphs)

    def __getitem__(self, index: int) -> Glyph:
        """Get a glyph by index.

        Args:
            index: Index of the glyph.

        Returns:
            The Glyph at the given index.
        """
        return self.glyphs[index]


def glyph_group_write_on(
    group: GlyphGroup,
    *,
    lag_ratio: float = 0.5,
    order: Ordering | None = None,
) -> Stagger:
    """Create a staggered write-on effect for every glyph in a group.

    Glyphs with borders use :func:`glyph_write_on`; glyphs without borders fade in their bodies
    over their staggered windows. Borders are not created implicitly.

    Args:
        group: The glyph group to reveal.
        lag_ratio: Delay between glyph reveal windows, as a fraction of each window.
        order: Ordering for the glyphs. Defaults to their natural order.

    Returns:
        A staggered effect that reveals each glyph.

    Raises:
        ValueError: If `lag_ratio` or `order` is invalid.
    """
    from anima.animation.effects import Fade, Stagger

    def reveal_glyph(child: Object) -> Effect:
        if not isinstance(child, Glyph):
            raise TypeError(f"Expected Glyph instance, got {type(child).__name__}")
        return glyph_write_on(child) if child.border is not None else Fade(child.body)

    return Stagger(group, lag_ratio=lag_ratio, order=order, children=group.glyphs, child_effect=reveal_glyph)


def _validate_part_fragment(name: str, fragment: str) -> None:
    """Reject group and comment boundaries that cannot be assigned reliably."""
    depth = 0
    index = 0
    while index < len(fragment):
        char = fragment[index]
        if char == "\\":
            index += 1
            start = index
            while index < len(fragment) and fragment[index].isascii() and fragment[index].isalpha():
                index += 1
            command = fragment[start:index]
            if command == "verb":
                if index < len(fragment) and fragment[index] == "*":
                    index += 1
                if index >= len(fragment) or fragment[index] in "\r\n":
                    raise TeXPartMappingError(f"Cannot map TeX part {name!r}: incomplete verbatim command.")
                delimiter = fragment[index]
                end = fragment.find(delimiter, index + 1)
                if end < 0 or "\n" in fragment[index + 1 : end] or "\r" in fragment[index + 1 : end]:
                    raise TeXPartMappingError(f"Cannot map TeX part {name!r}: verbatim content crosses a boundary.")
                index = end + 1
            elif not command:
                index += 1
            if index >= len(fragment) and command != "verb":
                raise TeXPartMappingError(f"Cannot map TeX part {name!r}: a control sequence ends at a part boundary.")
            continue
        if char == "%":
            end = fragment.find("\n", index + 1)
            if end < 0:
                raise TeXPartMappingError(f"Cannot map TeX part {name!r}: a comment crosses a part boundary.")
            index = end + 1
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth < 0:
                raise TeXPartMappingError(f"Cannot map TeX part {name!r}: a TeX group crosses a part boundary.")
        index += 1
    if depth:
        raise TeXPartMappingError(f"Cannot map TeX part {name!r}: a TeX group crosses a part boundary.")


def _scale_outline(outline: svgtools.Path, factor: float) -> svgtools.Path:
    """Scale Bézier control points directly, preserving exact shared endpoints.

    Args:
        outline: The SVG outline to scale.
        factor: The scaling factor.

    Returns:
        A new SVG outline with all control points scaled.
    """
    segments = []
    for segment in outline:
        if isinstance(segment, svgtools.Line):
            segments.append(svgtools.Line(segment.start * factor, segment.end * factor))
        elif isinstance(segment, svgtools.CubicBezier):
            segments.append(
                svgtools.CubicBezier(
                    segment.start * factor,
                    segment.control1 * factor,
                    segment.control2 * factor,
                    segment.end * factor,
                )
            )
        else:
            raise ValueError(f"Unsupported SVG segment type: {type(segment)}")
    return svgtools.Path(*segments)


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
