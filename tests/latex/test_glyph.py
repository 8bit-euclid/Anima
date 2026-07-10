"""Unit tests for Glyph, GlyphBorder, GlyphBody, and GlyphGroup classes."""

import pytest

from anima.latex.glyph import Glyph, GlyphBBox
from anima.latex.glyph_body import GlyphBody
from anima.latex.glyph_border import GlyphBorder
from anima.latex.glyph_group import GlyphGroup
from anima.latex.tex_object import TeXObject
from anima.primitives.chains import CurveLoop
from anima.primitives.mesh import Mesh
from anima.primitives.object import Object
from tests.test_utils import create_rect_path, create_rect_with_hole_path


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
        self.simple_path = create_rect_path()
        self.path_with_hole = create_rect_with_hole_path()

    def test_inheritance(self):
        """Test that GlyphBorder inherits from Object."""
        border = GlyphBorder(self.simple_path, name="TestBorder")
        assert isinstance(border, Object)

    def test_simple_path_creates_one_subpath(self):
        """Test that a simple path creates one CurveLoop subpath."""
        border = GlyphBorder(self.simple_path, name="TestBorder")
        assert len(border.subpaths) == 1
        assert isinstance(border.subpaths[0], CurveLoop)

    def test_path_with_hole_creates_two_subpaths(self):
        """Test that a path with a hole creates two CurveLoop subpaths."""
        border = GlyphBorder(self.path_with_hole, name="TestBorder")
        assert len(border.subpaths) == 2
        assert all(isinstance(sp, CurveLoop) for sp in border.subpaths)

    def test_subpaths_are_children(self):
        """Test that subpaths are added as children of the border."""
        border = GlyphBorder(self.simple_path, name="TestBorder")
        assert len(border.children) == 1
        assert border.children[0] == border.subpaths[0]

    def test_curves_property(self):
        """Test that the curves property returns all curves from all subpaths."""
        border = GlyphBorder(self.simple_path, name="TestBorder")
        curves = border.curves
        assert len(curves) > 0
        # A rectangle has 4 sides
        assert len(curves) == 4

    def test_name_propagation(self):
        """Test that name is propagated to subpaths."""
        border = GlyphBorder(self.simple_path, name="MyBorder")
        assert border.name == "MyBorder"
        assert border.subpaths[0].name == "MyBorder_loop_0"

    def test_invalid_path_raises(self):
        """Test that invalid path type raises assertion error."""
        with pytest.raises(AssertionError):
            GlyphBorder("not a path")


class TestGlyph:
    """Test suite for Glyph class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.path = create_rect_path()

    def test_inheritance(self):
        """Test that Glyph inherits from Object."""
        glyph = Glyph(self.path, name="TestGlyph")
        assert isinstance(glyph, Object)

    def test_border_and_body_created(self):
        """Test that border and body are created."""
        glyph = Glyph(self.path, name="TestGlyph")
        assert glyph.border is not None
        assert glyph.body is not None
        assert isinstance(glyph.border, GlyphBorder)
        assert isinstance(glyph.body, GlyphBody)

    def test_border_and_body_are_children(self):
        """Test that border and body are added as children."""
        glyph = Glyph(self.path, name="TestGlyph")
        assert len(glyph.children) == 2
        assert glyph.border in glyph.children
        assert glyph.body in glyph.children

    def test_bbox_y_inverted(self):
        """Test that bbox y-coordinates are inverted for Blender."""
        glyph = Glyph(self.path, name="TestGlyph")
        # Original path bbox has positive y, inverted should be negative
        assert glyph.bbox is not None

    def test_default_text_empty(self):
        """Test that text property defaults to empty string."""
        glyph = Glyph(self.path, name="TestGlyph")
        assert glyph.text == ""

    def test_name_propagation(self):
        """Test that name is propagated to border and body."""
        glyph = Glyph(self.path, name="MyGlyph")
        assert glyph.name == "MyGlyph"
        assert glyph.border.name == "MyGlyph_border"
        assert glyph.body.name == "MyGlyph_body"

    def test_invalid_path_raises(self):
        """Test that invalid path type raises assertion error."""
        with pytest.raises(AssertionError):
            Glyph("not a path")


class TestGlyphBody:
    """Test suite for GlyphBody class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.path = create_rect_path()
        self.border = GlyphBorder(self.path, name="TestBorder")

    def test_inheritance(self):
        """Test that GlyphBody inherits from Mesh."""
        body = GlyphBody(self.border, name="TestBody")
        assert isinstance(body, Mesh)
        assert isinstance(body, Object)

    def test_name(self):
        """Test that name is set correctly."""
        body = GlyphBody(self.border, name="MyBody")
        assert body.name == "MyBody"


class TestGlyphGroup:
    """Test suite for GlyphGroup class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.path1 = create_rect_path(x=0, y=0)
        self.path2 = create_rect_path(x=20, y=0)
        self.glyph1 = Glyph(self.path1, name="Glyph_A")
        self.glyph2 = Glyph(self.path2, name="Glyph_B")
        self.glyph1.text = "A"
        self.glyph2.text = "B"

    def test_inheritance(self):
        """Test that GlyphGroup inherits from Object."""
        group = GlyphGroup(name="TestGroup")
        assert isinstance(group, Object)

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

    def test_add_glyph(self):
        """Test adding glyphs to a group."""
        group = GlyphGroup(name="TestGroup")
        group.add_glyph(self.glyph1)
        assert len(group) == 1
        assert group.glyphs[0] == self.glyph1

        group.add_glyph(self.glyph2)
        assert len(group) == 2

    def test_glyphs_are_children(self):
        """Test that glyphs are added as children."""
        group = GlyphGroup([self.glyph1, self.glyph2], name="TestGroup")
        assert len(group.children) == 2
        assert self.glyph1 in group.children
        assert self.glyph2 in group.children

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
            group.add_glyph("not a glyph")
        with pytest.raises(TypeError):
            group.add_glyph(123)


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

    def test_add_subobject_valid(self):
        """Test adding a valid TeXObject as a subobject."""
        parent = TeXObject(name="Parent")
        child = TeXObject(name="Child")
        parent.add_subobject(child)
        assert child in parent.children
        assert child.parent is parent

    def test_add_subobject_type_error(self):
        """Test that adding non-TeXObject raises TypeError."""
        tex_obj = TeXObject(name="TestTeXObject")
        with pytest.raises(TypeError):
            tex_obj.add_subobject("not a TeXObject")
        with pytest.raises(TypeError):
            tex_obj.add_subobject(123)

    def test_name_property(self):
        """Test that name is set correctly."""
        tex_obj = TeXObject(name="MyTeXObject")
        assert tex_obj.name == "MyTeXObject"
