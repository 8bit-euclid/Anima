"""Tests for non-owning scene layouts."""

import math

import bpy
import pytest
from svgpathtools import parse_path

from anima.latex.glyph import Glyph
from anima.latex.glyph_group import GlyphGroup
from anima.layout import Layout, _normalize, _normalize_alignment
from anima.primitives.group import Group
from anima.primitives.lines import Segment
from anima.primitives.polytopes import Rectangle
from anima.scene.state import get_profile


@pytest.fixture(autouse=True)
def cleanup():
    yield
    for obj in list(bpy.data.objects):
        if obj.name.startswith("pytest_layout"):
            bpy.data.objects.remove(obj, do_unlink=True)


def rectangle(width, height, name):
    return Rectangle(width, height, name=f"pytest_layout_{name}")


def test_horizontal_tile_aligns_origins_and_leaves_existing_parent_unchanged():
    a, b = rectangle(2, 1, "a"), rectangle(1, 2, "b")
    group = Group([a, b], name="pytest_layout_parent")
    a.location = (10, 4, 1)
    b.location = (-2, -3, 2)

    layout = Layout([a, b]).tile(direction="right", gap=0.25)
    assert layout.place(at=(2, 5)) is layout

    assert tuple(a.location) == pytest.approx((3, 4, 1))
    assert tuple(b.location) == pytest.approx((4.75, 4, 2))
    assert a.parent is group and b.parent is group


def test_grid_sizes_columns_and_origins_with_nested_tile():
    a, b, c, d = (rectangle(*args) for args in [(2, 1, "a"), (1, 2, "b"), (1, 1, "c"), (1, 1, "d")])
    nested = Layout([c, d]).tile(direction="right", gap=0.2)
    layout = Layout.grid([[a, b], [nested]], column_gap=0.5, row_gap=0.75)
    layout.place()

    assert a.location.y == pytest.approx(b.location.y)
    assert b.location.x - a.location.x == pytest.approx(2.2)
    assert d.location.x - c.location.x == pytest.approx(1.2)
    assert c.location.y == pytest.approx(-3.25)
    assert all(obj.parent is None for obj in (a, b, c, d))


def test_nested_tile_preserves_origin_alignment_with_other_grid_cells():
    a = rectangle(1, 1, "a")
    b = rectangle(1, 2, "b")
    c = rectangle(1, 1, "c")
    row = Layout([b, c]).tile(direction="R")
    Layout.grid([[a, row]]).place()
    assert a.location.y == pytest.approx(b.location.y)
    assert b.location.y == pytest.approx(c.location.y)


def test_center_alignment_and_explicit_reflow_use_current_geometry():
    a, b = rectangle(2, 2, "a"), rectangle(1, 1, "b")
    layout = Layout([a, b]).tile(direction="down", gap=0.5, align="center")
    layout.place()
    assert a.location.x == pytest.approx(b.location.x)
    assert a.location.y - b.location.y == pytest.approx(2.0)

    a.scale = (1, 2, 1)
    layout.place()
    assert a.location.y - b.location.y == pytest.approx(3.0)


@pytest.mark.parametrize(("align", "expected"), [("origin", 0), ("center", -1)])
def test_grid_aligns_origins_or_geometry_centers(align, expected):
    child = rectangle(1, 1, "child")
    child.location = (0, 1, 0)
    a = Group([child], name="pytest_layout_group")
    b = rectangle(1, 1, "b")

    Layout.grid([[a, b]], align_y=align).place()

    assert a.location.y - b.location.y == pytest.approx(expected)


def test_scaled_rotated_objects_use_shared_parent_coordinates():
    a, b = rectangle(2, 1, "a"), rectangle(1, 1, "b")
    group = Group([a, b], name="pytest_layout_parent")
    group.location = (10, 5, 0)
    group.rotation = (0, 0, math.pi / 4)
    a.rotation = (0, 0, math.pi / 2)
    a.scale = (2, 1, 1)

    Layout([a, b]).tile(direction="right", gap=0.5).place(at=(0, 0))

    assert tuple(a.location) == pytest.approx((0.5, -2, 0), abs=1e-6)
    assert tuple(b.location) == pytest.approx((2, -2, 0), abs=1e-6)
    assert a.parent is group and b.parent is group


def test_safe_area_rejects_overflow_without_moving_any_object():
    a, b = rectangle(2, 1, "a"), rectangle(2, 1, "b")
    a.location = (3, 4, 5)
    b.location = (-4, -5, 6)
    layout = Layout([a, b]).tile(direction="right", gap=get_profile().safe_size[0])

    with pytest.raises(ValueError, match="exceeds"):
        layout.place_in_safe_area()
    assert tuple(a.location) == pytest.approx((3, 4, 5))
    assert tuple(b.location) == pytest.approx((-4, -5, 6))


def test_safe_area_anchors_layout_at_top_left():
    a = rectangle(2, 1, "a")
    Layout([a]).place_in_safe_area()
    width, height = get_profile().safe_size
    assert tuple(a.location) == pytest.approx((-width / 2 + 1, height / 2 - 0.5, 0))


def test_hidden_glyph_and_transformed_curves_have_measurable_bounds():
    glyph = Glyph(parse_path("M0 0 L2 0 L2 1 L0 1 Z"), name="pytest_layout_glyph", with_border=True)
    group = GlyphGroup([glyph], name="pytest_layout_glyph_group")
    group.hide()
    line = Segment((0, 0), (2, 0), name="pytest_layout_line")
    line.rotation = (0, 0, math.pi / 2)
    Layout([group, line]).tile(direction="right", gap=1).place()

    assert line.location.x > group.location.x + 2
    assert group.parent is None and glyph.parent is group


@pytest.mark.parametrize("gap", [-1, float("inf"), float("nan")])
def test_invalid_gaps_are_rejected(gap):
    with pytest.raises(ValueError, match="gap"):
        Layout([]).tile(gap=gap)


def test_duplicate_objects_and_mixed_parents_are_rejected_before_moving():
    a, b = rectangle(1, 1, "a"), rectangle(1, 1, "b")
    parent = Group([a], name="pytest_layout_parent")
    a.location = (1, 2, 3)
    with pytest.raises(ValueError, match="more than once"):
        Layout([a, Layout([a])]).place()
    with pytest.raises(ValueError, match="same parent"):
        Layout([a, b]).place()
    with pytest.raises(ValueError, match="root-level"):
        Layout([a]).place_in_safe_area()
    assert a.parent is parent
    assert tuple(a.location) == pytest.approx((1, 2, 3))


def test_empty_geometry_is_rejected_without_moving_other_objects():
    a = rectangle(1, 1, "a")
    empty = Group(name="pytest_layout_empty")
    a.location = (1, 2, 3)
    with pytest.raises(ValueError, match="no geometry"):
        Layout([a, empty]).place()
    assert tuple(a.location) == pytest.approx((1, 2, 3))


def test_unsupported_constraint_and_parent_inverse_do_not_move_objects():
    a, b = rectangle(1, 1, "a"), rectangle(1, 1, "b")
    group = Group([a, b], name="pytest_layout_parent")
    a.location = (1, 2, 3)
    constraint = b.object.constraints.new("LIMIT_LOCATION")
    with pytest.raises(ValueError, match="constraints"):
        Layout([a, b]).place()
    b.object.constraints.remove(constraint)
    b.object.matrix_parent_inverse[0][3] = 2
    with pytest.raises(ValueError, match="parent inverse"):
        Layout([a, b]).place()
    assert tuple(a.location) == pytest.approx((1, 2, 3))
    assert a.parent is group and b.parent is group


@pytest.mark.parametrize(
    ("direction", "expected"),
    [("R", (1.75, 0)), ("L", (-1.75, 0)), ("U", (0, 1.75)), ("D", (0, -1.75))],
)
def test_tile_directions_place_successive_items(direction, expected):
    a, b = rectangle(2, 2, "a"), rectangle(1, 1, "b")
    Layout([a, b]).tile(direction=direction, gap=0.25).place()
    assert (b.location.x - a.location.x, b.location.y - a.location.y) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("direction", "align", "expected"),
    [("R", "top", 0.5), ("R", "bottom", -0.5), ("D", "left", -0.5), ("D", "right", 0.5)],
)
def test_tile_aligns_cross_axis_edges(direction, align, expected):
    a, b = rectangle(2, 2, "a"), rectangle(1, 1, "b")
    Layout([a, b]).tile(direction=direction, align=align).place()
    actual = b.location.y - a.location.y if direction == "R" else b.location.x - a.location.x
    assert actual == pytest.approx(expected)


def test_grid_aligns_cells_on_both_axes_and_sizes_origin_aligned_columns():
    a, b = rectangle(2, 2, "a"), rectangle(1, 1, "b")
    c, d = rectangle(1, 1, "c"), rectangle(2, 2, "d")
    Layout.grid([[a, b], [c, d]], column_gap=0.5, row_gap=0.5, align_x="right", align_y="top").place()
    assert a.location.x + 1 == pytest.approx(c.location.x + 0.5)
    assert b.location.x + 0.5 == pytest.approx(d.location.x + 1)
    assert a.location.y + 1 == pytest.approx(b.location.y + 0.5)
    assert c.location.y + 0.5 == pytest.approx(d.location.y + 1)
    assert d.location.x - 1 - (a.location.x + 1) == pytest.approx(0.5)

    child = rectangle(1, 1, "child")
    child.location = (3, 0, 0)
    offset_group = Group([child], name="pytest_layout_offset_group")
    Layout.grid([[a, b], [offset_group, d]], column_gap=0.5, align_x="origin").place()
    assert a.location.x == pytest.approx(offset_group.location.x)
    assert d.location.x - 1 - (offset_group.location.x + 3.5) == pytest.approx(0.5)


@pytest.mark.parametrize(
    ("anchor", "expected"),
    [
        ("top_left", (1, -0.5)),
        ("TR", (-1, -0.5)),
        ("BR", (-1, 0.5)),
        ("bottom_left", (1, 0.5)),
        ("center", (0, 0)),
        ("left", (1, 0)),
        ("right", (-1, 0)),
        ("top", (0, -0.5)),
        ("bottom", (0, 0.5)),
    ],
)
def test_place_supports_all_anchors(anchor, expected):
    a = rectangle(2, 1, "a")
    Layout([a]).place(at=(3, 4), anchor=anchor)
    assert (a.location.x, a.location.y) == pytest.approx((3 + expected[0], 4 + expected[1]))


def test_safe_area_anchor_and_overflow_remain_atomic():
    a = rectangle(2, 1, "a")
    width, height = get_profile().safe_size
    Layout([a]).place_in_safe_area(anchor="BR")
    assert (a.location.x, a.location.y) == pytest.approx((width / 2 - 1, -height / 2 + 0.5))
    a.location = (3, 4, 5)
    with pytest.raises(ValueError, match="exceeds"):
        Layout([a]).place(at=(0, 0), anchor="center", bounds=(-0.5, -0.5, 0.5, 0.5))
    assert tuple(a.location) == pytest.approx((3, 4, 5))


@pytest.mark.parametrize(
    ("direction", "align", "expected"),
    [("R", "top", (4.75, 5.5)), ("L", "bottom", (1.25, 4.5)), ("U", "left", (2.5, 6.75)), ("D", "right", (3.5, 3.25))],
)
def test_next_to_positions_only_the_target_in_shared_parent_frame(direction, align, expected):
    reference, target = rectangle(2, 2, "reference"), rectangle(1, 1, "target")
    parent = Group([reference, target], name="pytest_layout_parent")
    parent.rotation = (0, 0, math.pi / 4)
    reference.location = (3, 5, 7)
    target.location = (-3, -5, 8)
    target.next_to(reference, direction=direction, gap=0.25, align=align)
    assert tuple(target.location) == pytest.approx((*expected, 8))
    assert tuple(reference.location) == pytest.approx((3, 5, 7))
    assert reference.parent is parent and target.parent is parent


def test_next_to_recalculates_after_geometry_changes_and_rejects_invalid_input():
    reference, target = rectangle(2, 1, "reference"), rectangle(1, 1, "target")
    target.next_to(reference)
    assert target.location.x == pytest.approx(2)
    reference.scale = (2, 1, 1)
    target.next_to(reference)
    assert target.location.x == pytest.approx(3)
    previous = tuple(target.location)
    for kwargs in ({"direction": "horizontal"}, {"align": "left"}, {"gap": -1}):
        with pytest.raises(ValueError):
            target.next_to(reference, **kwargs)
    with pytest.raises(ValueError, match="more than once"):
        target.next_to(target)
    with pytest.raises(TypeError, match="reference"):
        target.next_to(None)
    Group([reference], name="pytest_layout_parent")
    with pytest.raises(ValueError, match="same parent"):
        target.next_to(reference)
    assert tuple(target.location) == pytest.approx(previous)


def test_invalid_layout_alignment_and_anchor_are_rejected_without_moving():
    a = rectangle(1, 1, "a")
    a.location = (2, 3, 4)
    with pytest.raises(ValueError, match="alignment"):
        Layout([a]).tile(direction="R", align="left")
    with pytest.raises(ValueError, match="alignment"):
        Layout.grid([[a]], align_x="top")
    with pytest.raises(ValueError, match="anchor"):
        Layout([a]).place(anchor="invalid")
    with pytest.raises(ValueError, match="anchor"):
        Layout([a]).place_in_safe_area(anchor="invalid")
    assert tuple(a.location) == pytest.approx((2, 3, 4))


def test_aliases_normalize_in_each_context():
    directions = ("right", "left", "up", "down")
    anchors = ("center", "left", "right", "top", "bottom", "top_left", "top_right", "bottom_left", "bottom_right")
    cases = [
        ("r", "right", "x"),
        ("l", "left", "x"),
        ("u", "up", None),
        ("d", "down", None),
        ("c", "center", "xy"),
        ("t", "top", "y"),
        ("b", "bottom", "y"),
        ("tl", "top_left", None),
        ("tr", "top_right", None),
        ("bl", "bottom_left", None),
        ("br", "bottom_right", None),
    ]
    for short, full, axes in cases:
        for spelling in (short, short.upper(), full, full.upper(), full.title()):
            if full in directions:
                assert _normalize(spelling, directions, "direction") == full
            if full in anchors:
                assert _normalize(spelling, anchors, "anchor") == full
            if axes:
                for axis in axes:
                    assert _normalize_alignment(spelling, axis) == full
    for spelling in ("origin", "ORIGIN", "Origin"):
        assert _normalize_alignment(spelling, "x") == "origin"
        assert _normalize_alignment(spelling, "y") == "origin"


def test_direction_aliases_match_for_tile_and_next_to():
    a, b = rectangle(2, 2, "a"), rectangle(1, 1, "b")
    Layout([a, b]).tile(direction="right").place()
    expected_tile = (tuple(a.location), tuple(b.location))
    b.next_to(a, direction="right")
    expected_relative = tuple(b.location)
    for spelling in ("R", "r", "RIGHT", "Right"):
        Layout([a, b]).tile(direction=spelling).place()
        assert tuple(a.location) == pytest.approx(expected_tile[0])
        assert tuple(b.location) == pytest.approx(expected_tile[1])
        b.next_to(a, direction=spelling)
        assert tuple(b.location) == pytest.approx(expected_relative)


def test_alignment_aliases_match_for_tile_grid_and_next_to():
    a, b = rectangle(2, 2, "a"), rectangle(1, 1, "b")
    c, d = rectangle(1, 1, "c"), rectangle(2, 2, "d")
    Layout([a, b]).tile(direction="right", align="top").place()
    expected_tile = (tuple(a.location), tuple(b.location))
    b.next_to(a, direction="right", align="top")
    expected_relative = tuple(b.location)
    Layout.grid([[a, b], [c, d]], align_x="right", align_y="top").place()
    expected_grid = [tuple(obj.location) for obj in (a, b, c, d)]
    for spelling in ("T", "t", "TOP", "Top"):
        Layout([a, b]).tile(direction="right", align=spelling).place()
        assert tuple(a.location) == pytest.approx(expected_tile[0])
        assert tuple(b.location) == pytest.approx(expected_tile[1])
        b.next_to(a, direction="right", align=spelling)
        assert tuple(b.location) == pytest.approx(expected_relative)
        Layout.grid([[a, b], [c, d]], align_x="R", align_y=spelling).place()
        for obj, expected in zip((a, b, c, d), expected_grid, strict=True):
            assert tuple(obj.location) == pytest.approx(expected)


def test_anchor_aliases_match_for_place_and_safe_area():
    a = rectangle(2, 1, "a")
    layout = Layout([a])
    layout.place(at=(2, 3), anchor="bottom_right")
    expected_place = tuple(a.location)
    layout.place_in_safe_area(anchor="bottom_right")
    expected_safe = tuple(a.location)
    for spelling in ("BR", "br", "BOTTOM_RIGHT", "Bottom_Right"):
        layout.place(at=(2, 3), anchor=spelling)
        assert tuple(a.location) == pytest.approx(expected_place)
        layout.place_in_safe_area(anchor=spelling)
        assert tuple(a.location) == pytest.approx(expected_safe)


def test_origin_is_case_insensitive_and_invalid_short_forms_are_rejected():
    a, b = rectangle(2, 2, "a"), rectangle(1, 1, "b")
    Layout([a, b]).tile(direction="r", align="ORIGIN").place()
    assert a.location.y == pytest.approx(b.location.y)
    with pytest.raises(ValueError, match="direction"):
        b.next_to(a, direction="UR")
    with pytest.raises(ValueError, match="alignment"):
        Layout.grid([[a]], align_x="u")
    with pytest.raises(ValueError, match="anchor"):
        Layout([a]).place(anchor="d")


@pytest.mark.parametrize("direction", ["rightward", "ur", "", None])
def test_invalid_direction_does_not_change_configured_layout(direction):
    a, b = rectangle(2, 2, "a"), rectangle(1, 1, "b")
    layout = Layout([a, b]).tile(direction="L")
    with pytest.raises(ValueError, match="direction"):
        layout.tile(direction=direction)
    layout.place()
    assert b.location.x < a.location.x
