"""Unit tests for Glyph, GlyphBorder, GlyphBody, and GlyphGroup classes."""

from dataclasses import replace
from unittest.mock import MagicMock

import pytest
import svgpathtools as svgtools

from anima.latex.glyph import Glyph, GlyphBBox, glyph_write_on
from anima.latex.glyph_body import GlyphBody
from anima.latex.glyph_border import GlyphBorder
from anima.latex.glyph_group import GlyphGroup, _format_glyph_name, _scale_outline
from anima.latex.tex_object import TeXObject
from anima.primitives.chains import CurveLoop
from anima.primitives.group import Group
from anima.primitives.mesh import Mesh
from anima.primitives.object import Object
from anima.scene.profile import FRAME_16X9_V1
from anima.scene.state import reset_profile, set_profile
from tests.utils.test_utils import create_rect_path, create_rect_with_hole_path


class TestGlyphBBox:
    """Test suite for GlyphBBox dataclass."""

    def test_default_values(self):
        """Test default bounding box values."""
        bbox = GlyphBBox()
        assert bbox.x_min == 0
        assert bbox.x_max == 0
        assert bbox.y_min == 0
        assert bbox.y_max == 0

    def test_custom_values(self):
        """Test custom bounding box values."""
        bbox = GlyphBBox(x_min=-5, x_max=15, y_min=-10, y_max=20)
        assert bbox.x_min == -5
        assert bbox.x_max == 15
        assert bbox.y_min == -10
        assert bbox.y_max == 20


class TestGlyphBorder:
    """Test suite for GlyphBorder class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.simple_outline = create_rect_path()
        self.outline_with_hole = create_rect_with_hole_path()

    def test_inheritance(self):
        """Test that GlyphBorder inherits from Object."""
        border = GlyphBorder(self.simple_outline, name="TestBorder")
        assert isinstance(border, Object)

    def test_simple_outline_creates_one_subpath(self):
        """Test that a simple outline creates one CurveLoop subpath."""
        border = GlyphBorder(self.simple_outline, name="TestBorder")
        assert len(border.subpaths) == 1
        assert isinstance(border.subpaths[0], CurveLoop)

    def test_outline_with_hole_creates_two_subpaths(self):
        """Test that an outline with a hole creates two CurveLoop subpaths."""
        border = GlyphBorder(self.outline_with_hole, name="TestBorder")
        assert len(border.subpaths) == 2
        assert all(isinstance(sp, CurveLoop) for sp in border.subpaths)

    def test_subpaths_are_children(self):
        """Test that subpaths are added as children of the border."""
        border = GlyphBorder(self.simple_outline, name="TestBorder")
        children = border.children
        assert len(children) == 1
        assert children[0] == border.subpaths[0]

    def test_curves_property(self):
        """Test that the curves property returns all curves from all subpaths."""
        border = GlyphBorder(self.simple_outline, name="TestBorder")
        curves = border.curves
        assert len(curves) > 0
        # A rectangle has 4 sides
        assert len(curves) == 4

    def test_name_propagation(self):
        """Test that name is propagated to subpaths."""
        border = GlyphBorder(self.simple_outline, name="MyBorder")
        assert border.name == "MyBorder"
        assert border.subpaths[0].name == "MyBorder_loop_0"

    def test_invalid_outline_raises(self):
        """Test that an invalid outline type raises assertion error."""
        with pytest.raises(AssertionError):
            GlyphBorder("not an outline")


class TestGlyph:
    """Test suite for Glyph class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.outline = create_rect_path()

    def test_inheritance(self):
        """Test that Glyph inherits from Object."""
        glyph = Glyph(self.outline, name="TestGlyph")
        assert isinstance(glyph, Object)

    def test_border_and_body_created(self):
        """Test that the filled body is created by default without a border."""
        glyph = Glyph(self.outline, name="TestGlyph")
        assert glyph.border is None
        assert glyph.body is not None
        assert isinstance(glyph.body, GlyphBody)

    def test_border_and_body_are_children(self):
        """Test that an explicitly requested border and the body are children."""
        glyph = Glyph(self.outline, name="TestGlyph", with_border=True)
        children = glyph.children
        assert len(children) == 2
        assert glyph.border in children
        assert glyph.body in children

    def test_default_body_matches_border_backed_body(self):
        body_only = Glyph(self.outline, name="BodyOnly")
        outlined = Glyph(self.outline, name="Outlined", with_border=True)

        assert [tuple(vertex) for vertex in body_only.body._vertices] == [
            tuple(vertex) for vertex in outlined.body._vertices
        ]
        assert body_only.body._faces == outlined.body._faces

    def test_bbox_y_inverted(self):
        """Test that bbox y-coordinates are inverted for Blender."""
        outline = create_rect_path(x=2, y=3, width=7, height=11)

        glyph = Glyph(outline, name="TestGlyph")

        assert glyph.bbox.x_min == 2
        assert glyph.bbox.x_max == 9
        assert glyph.bbox.y_min == -3
        assert glyph.bbox.y_max == -14

    def test_default_text_empty(self):
        """Test that text property defaults to empty string."""
        glyph = Glyph(self.outline, name="TestGlyph")
        assert glyph.text == ""

    def test_name_propagation(self):
        """Test that name is propagated to border and body."""
        glyph = Glyph(self.outline, name="MyGlyph", with_border=True)
        assert glyph.name == "MyGlyph"
        assert glyph.border.name == "MyGlyph_border"
        assert glyph.body.name == "MyGlyph_body"

    def test_copy_has_independent_glyph_materials(self):
        glyph = Glyph(self.outline, name="pytest_glyph_copy", with_border=True)
        glyph.set_color((1.0, 0.0, 0.0, 1.0))
        copied = glyph.copy()

        assert copied.body.object.data.materials[0] != glyph.body.object.data.materials[0]
        assert copied.border.curves[0].object.data.materials[0] != glyph.border.curves[0].object.data.materials[0]
        assert all(
            curve.object.data.materials[0] == copied.border.curves[0].object.data.materials[0]
            for curve in copied.border.curves
        )
        copied.set_color((0.0, 0.0, 1.0, 1.0))
        copied.set_opacity(0.25)
        assert glyph.body.color == pytest.approx((1.0, 0.0, 0.0, 1.0))
        assert glyph.border.curves[0].color == pytest.approx((1.0, 0.0, 0.0, 1.0))
        assert copied.body.color == pytest.approx((0.0, 0.0, 1.0, 0.25))
        assert copied.border.curves[0].color == pytest.approx((0.0, 0.0, 1.0, 0.25))
        glyph.set_color((0.0, 1.0, 0.0, 1.0))
        assert copied.body.color == pytest.approx((0.0, 0.0, 1.0, 0.25))
        assert copied.border.curves[0].color == pytest.approx((0.0, 0.0, 1.0, 0.25))

    def test_border_curves_share_material_and_style_as_one_border(self):
        glyph = Glyph(self.outline, name="SharedBorder", with_border=True)
        glyph.set_color((1.0, 0.0, 0.0, 1.0))

        materials = [curve.object.data.materials[0] for curve in glyph.border.curves]
        assert all(material == materials[0] for material in materials)
        glyph.border.curves[0].set_color((0.0, 0.0, 1.0, 1.0))
        assert all(curve.color == pytest.approx((0.0, 0.0, 1.0, 1.0)) for curve in glyph.border.curves)

    def test_invalid_outline_raises(self):
        """Test that an invalid outline type raises assertion error."""
        with pytest.raises(AssertionError):
            Glyph("not an outline")

    def test_write_on_requires_an_explicit_border(self):
        with pytest.raises(ValueError, match="with_border=True"):
            glyph_write_on(Glyph(self.outline))


class TestGlyphBody:
    """Test suite for GlyphBody class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.outline = create_rect_path()

    def test_inheritance(self):
        """Test that GlyphBody inherits from Mesh."""
        body = GlyphBody(self.outline, name="TestBody")
        assert isinstance(body, Mesh)
        assert isinstance(body, Object)

    def test_name(self):
        """Test that name is set correctly."""
        body = GlyphBody(self.outline, name="MyBody")
        assert body.name == "MyBody"

    def test_outline_creates_mesh(self):
        body = GlyphBody(self.outline)
        assert body._vertices
        assert body._faces


class TestGlyphGroup:
    """Test suite for GlyphGroup class."""

    def test_format_glyph_name(self):
        assert _format_glyph_name(1, "A", 8) == "01-A"
        assert _format_glyph_name(8, "\n", 8) == "08-U+000A"
        assert _format_glyph_name(1, None, 100) == "001-U+?"
        assert _format_glyph_name(2, None, 3, "rule") == "02-rule"
        assert _format_glyph_name(3, "\ue050", 3, "summationtext") == "03-summationtext"

    def test_from_tex_string_builds_named_positioned_glyphs_in_order(self, monkeypatch):
        positions = [
            ("g0-65", (1.0, 2.0), "A", None),
            ("rule-1", (0.0, 0.0), None, "rule"),
            ("g1-private", (3.0, 4.0), "\ue050", "summationtext"),
        ]
        processor = MagicMock()
        processor.return_value.__enter__.return_value = (
            {"g0-65": self.outline1, "rule-1": self.outline2, "g1-private": self.outline1},
            positions,
        )
        monkeypatch.setattr("anima.latex.glyph_group.TeXDocumentProcessor", processor)

        group = GlyphGroup.from_tex_string("A+?", name="Equation")

        assert group.name == "Equation"
        assert [glyph.name for glyph in group] == ["01-A", "02-rule", "03-summationtext"]
        assert [glyph.text for glyph in group] == ["A", "", "\ue050"]
        assert group.text == "A\ue050"
        factor = FRAME_16X9_V1.tex_point_size / (72 / 72.27)
        assert [tuple(glyph.location) for glyph in group] == [
            pytest.approx((factor, 2 * factor, 0.0)),
            pytest.approx((0.0, 0.0, 0.0)),
            pytest.approx((3 * factor, 4 * factor, 0.0)),
        ]
        assert group[0].bbox.x_max == pytest.approx(self.outline1.bbox()[1] * factor)
        assert group[1].bbox.x_min == pytest.approx(self.outline2.bbox()[0] * factor)
        assert tuple(group.scale) == pytest.approx((1, 1, 1))
        assert all(glyph in group.children for glyph in group)
        assert all(glyph.border is None for glyph in group)

    def test_from_tex_string_can_create_borders(self, monkeypatch):
        processor = MagicMock()
        processor.return_value.__enter__.return_value = ({"a": self.outline1}, [("a", (0, 0), "A", None)])
        monkeypatch.setattr("anima.latex.glyph_group.TeXDocumentProcessor", processor)

        group = GlyphGroup.from_tex_string("A", with_borders=True)

        assert isinstance(group[0].border, GlyphBorder)

    def test_from_tex_string_typesets_font_size_and_uses_fixed_scene_conversion(self, monkeypatch):
        processor = MagicMock()
        processor.return_value.__enter__.return_value = (
            {"a": self.outline1},
            [("a", (3, 4), "A", None)],
        )
        monkeypatch.setattr("anima.latex.glyph_group.TeXDocumentProcessor", processor)
        small = GlyphGroup.from_tex_string("A", font_size=7.5)
        large = GlyphGroup.from_tex_string("A", font_size=15)
        small_document = str(processor.call_args_list[0].args[0])
        large_document = str(processor.call_args_list[1].args[0])
        assert r"\fontsize{7.5}{9.0}\selectfont" in small_document
        assert r"\fontsize{15}{18.0}\selectfont" in large_document
        assert tuple(large[0].location) == pytest.approx(tuple(small[0].location))
        assert large[0].bbox.x_max == pytest.approx(small[0].bbox.x_max)

    def test_from_tex_string_uses_supplied_profile(self, monkeypatch):
        processor = MagicMock()
        processor.return_value.__enter__.return_value = ({"a": self.outline1}, [("a", (3, 4), "A", None)])
        monkeypatch.setattr("anima.latex.glyph_group.TeXDocumentProcessor", processor)
        profile = replace(FRAME_16X9_V1, body_font_size=12.5, tex_point_size=0.16)

        set_profile(profile)
        try:
            group = GlyphGroup.from_tex_string("A")
            assert r"\fontsize{12.5}{15.0}\selectfont" in str(processor.call_args.args[0])
            factor = profile.tex_point_size / (72 / 72.27)
            assert tuple(group[0].location) == pytest.approx((3 * factor, 4 * factor, 0))
            GlyphGroup.from_tex_string("A", font_size=20)
            assert r"\fontsize{20}{24.0}\selectfont" in str(processor.call_args.args[0])
        finally:
            reset_profile()

    def test_scale_outline_preserves_exact_closure_for_cubic_curves(self):
        start = complex(6.8242, -3.3276)
        outline = svgtools.Path(
            svgtools.CubicBezier(start, 5.1 - 4.2j, 3.2 - 2.4j, 2.3 - 1.7j),
            svgtools.CubicBezier(2.3 - 1.7j, 1.7 - 0.1j, 4.9 - 5.2j, start),
        )
        scaled = _scale_outline(outline, 0.12045)
        assert scaled.isclosed()
        assert scaled[0].end == scaled[1].start
        assert scaled[0].start == scaled[1].end
        assert scaled[0].control1 == outline[0].control1 * 0.12045

    @pytest.mark.parametrize("font_size", [0, -1, float("inf"), float("nan")])
    def test_from_tex_string_rejects_invalid_font_size(self, font_size):
        with pytest.raises(ValueError, match="font_size"):
            GlyphGroup.from_tex_string("A", font_size=font_size)

    def setup_method(self):
        """Set up test fixtures."""
        self.outline1 = create_rect_path(x=0, y=0)
        self.outline2 = create_rect_path(x=20, y=0)
        self.glyph1 = Glyph(self.outline1, name="Glyph_A")
        self.glyph2 = Glyph(self.outline2, name="Glyph_B")
        self.glyph1.text = "A"
        self.glyph2.text = "B"

    def test_inheritance(self):
        """Test that GlyphGroup inherits from Group (and therefore Object)."""
        group = GlyphGroup(name="TestGroup")
        assert isinstance(group, Group)
        assert isinstance(group, Object)

    def test_inherited_add_stays_consistent(self):
        """Test that Group.add and remove_child keep glyphs in sync with children."""
        group = GlyphGroup(name="TestGroup")
        group.add(self.glyph1, self.glyph2)
        assert group.glyphs == [self.glyph1, self.glyph2]
        group.remove_child(self.glyph1)
        assert group.glyphs == [self.glyph2]
        assert len(group) == 1

    def test_empty_group(self):
        """Test creating an empty group."""
        group = GlyphGroup(name="EmptyGroup")
        assert len(group) == 0
        assert group.glyphs == []
        assert group.text == ""

    def test_initialize_with_glyphs(self):
        """Test initializing group with glyphs."""
        group = GlyphGroup([self.glyph1, self.glyph2], name="TestGroup")
        assert len(group) == 2
        assert group.glyphs == [self.glyph1, self.glyph2]

    def test_add(self):
        """Test adding glyphs to a group."""
        group = GlyphGroup(name="TestGroup")
        group.add(self.glyph1)
        assert len(group) == 1
        assert group.glyphs[0] == self.glyph1

        group.add(self.glyph2)
        assert len(group) == 2

    def test_glyphs_are_children(self):
        """Test that glyphs are added as children."""
        group = GlyphGroup([self.glyph1, self.glyph2], name="TestGroup")
        children = group.children
        assert len(children) == 2
        assert self.glyph1 in children
        assert self.glyph2 in children

    def test_text_property(self):
        """Test that text property concatenates glyph texts."""
        group = GlyphGroup([self.glyph1, self.glyph2], name="TestGroup")
        assert group.text == "AB"

    def test_iteration(self):
        """Test iterating over glyphs."""
        group = GlyphGroup([self.glyph1, self.glyph2], name="TestGroup")
        glyphs = list(group)
        assert glyphs == [self.glyph1, self.glyph2]

    def test_indexing(self):
        """Test accessing glyphs by index."""
        group = GlyphGroup([self.glyph1, self.glyph2], name="TestGroup")
        assert group[0] == self.glyph1
        assert group[1] == self.glyph2

    def test_add_non_glyph_raises(self):
        """Test that adding non-Glyph raises TypeError."""
        group = GlyphGroup(name="TestGroup")
        with pytest.raises(TypeError):
            group.add("not a glyph")
        with pytest.raises(TypeError):
            group.add_child(123)
        with pytest.raises(TypeError):
            group.add(Object(name="plain"))
        assert len(group) == 0


class TestTeXObject:
    """Test suite for TeXObject class."""

    def test_inheritance(self):
        """Test that TeXObject inherits from Object."""
        tex_obj = TeXObject(name="TestTeXObject")
        assert isinstance(tex_obj, Object)

    def test_default_text_empty(self):
        """Test that text property defaults to empty string."""
        tex_obj = TeXObject(name="TestTeXObject")
        assert tex_obj.text == ""

    def test_default_rendered_true(self):
        """Test that rendered property defaults to True."""
        tex_obj = TeXObject(name="TestTeXObject")
        assert tex_obj.rendered is True

    def test_default_sub_objects_empty(self):
        """Test that sub_objects defaults to empty tuple."""
        tex_obj = TeXObject(name="TestTeXObject")
        assert tex_obj.sub_objects == ()

    def test_text_setter(self):
        """Test setting the text property."""
        tex_obj = TeXObject(name="TestTeXObject")
        tex_obj.text = "Hello"
        assert tex_obj.text == "Hello"

    def test_rendered_setter(self):
        """Test setting the rendered property."""
        tex_obj = TeXObject(name="TestTeXObject")
        tex_obj.rendered = False
        assert tex_obj.rendered is False

    def test_add_child_valid(self):
        """Test adding a valid TeXObject as a child."""
        parent = TeXObject(name="Parent")
        child = TeXObject(name="Child")
        parent.add_child(child)
        assert child in parent.children
        assert child.parent is parent

    def test_add_child_type_error(self):
        """Test that adding non-TeXObject raises TypeError."""
        tex_obj = TeXObject(name="TestTeXObject")
        with pytest.raises(TypeError):
            tex_obj.add_child("not a TeXObject")
        with pytest.raises(TypeError):
            tex_obj.add_child(123)

    def test_name_property(self):
        """Test that name is set correctly."""
        tex_obj = TeXObject(name="MyTeXObject")
        assert tex_obj.name == "MyTeXObject"
