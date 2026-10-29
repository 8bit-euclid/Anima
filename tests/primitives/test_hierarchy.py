"""Tests for the Anima/Blender hierarchy consistency checker and the nesting it guards."""

import bpy
import pytest

from anima.diagnostics.hierarchy import check_hierarchy
from anima.primitives.bezier_spline import BezierSpline
from anima.primitives.group import Group
from anima.primitives.points import Empty


@pytest.fixture(autouse=True)
def cleanup():
    yield
    for obj in list(bpy.data.objects):
        if obj.name.startswith("pytest_"):
            bpy.data.objects.remove(obj, do_unlink=True)


def _mine(problems):
    return [p for p in problems if p.startswith("pytest_")]


def test_consistent_tree_has_no_problems():
    group = Group(name="pytest_root")
    Empty(name="pytest_driver", parent=group)
    spline = BezierSpline([(0, 0), (1, 1)], name="pytest_spline")
    group.add(spline)
    assert _mine(check_hierarchy()) == []


def test_unwrapped_blender_object_is_reported():
    bpy.context.collection.objects.link(bpy.data.objects.new("pytest_stray", None))
    assert any("pytest_stray" in p for p in check_hierarchy())


def test_parent_mismatch_is_reported():
    group = Group(name="pytest_root")
    child = Empty(name="pytest_child", parent=group)
    child.object.parent = None
    assert any("pytest_child" in p for p in check_hierarchy())


def test_empty_is_a_dataless_blender_empty():
    e = Empty(name="pytest_e")
    assert e.object.type == "EMPTY"


def test_profile_is_named_after_its_spline():
    spline = BezierSpline([(0, 0), (1, 1)], name="pytest_spline")
    assert spline.object.data.bevel_object.name == "pytest_spline_profile"
    spline.name = "pytest_renamed"
    assert spline.object.data.bevel_object.name == "pytest_renamed_profile"
    bpy.data.objects.remove(spline.object.data.bevel_object, do_unlink=True)


def test_dashed_curve_adopts_base_and_names_dashes():
    group = Group(name="pytest_root")
    spline = BezierSpline([(0, 0), (1, 1)], name="pytest_spline")
    group.add(spline)
    dashed = spline.make_dashed()
    assert dashed.name == "pytest_spline_dashed"
    assert dashed.parent is group
    assert spline.parent is dashed
    assert spline in dashed.children
    assert all(c.name.startswith("pytest_spline_dashed_dash") for c in dashed.children if c is not spline)
    assert _mine(check_hierarchy()) == []
    dashed.unhide()
    assert spline.object.hide_viewport
