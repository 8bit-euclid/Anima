"""Tests for Group, parenting rules and viewport highlighting."""

import bpy
import pytest

from anima.primitives.group import Group
from anima.primitives.polytopes import Rectangle


@pytest.fixture(autouse=True)
def cleanup():
    yield
    for obj in list(bpy.data.objects):
        if obj.name.startswith("pytest_"):
            bpy.data.objects.remove(obj, do_unlink=True)


def _rect(name):
    return Rectangle(1, 1, name=f"pytest_{name}")


def test_group_is_dataless_with_hidden_axes():
    group = Group(name="pytest_group")
    assert group.object.type == "EMPTY"
    assert group.object.data is None
    assert group.object.empty_display_size < 1e-3


def test_add_subobject_is_idempotent_for_same_parent():
    group = Group(name="pytest_group")
    a = _rect("a")
    group.add(a, a)
    group.add_subobject(a)
    assert group.subobjects == [a]


def test_adding_to_a_second_parent_raises():
    g1, g2 = Group(name="pytest_g1"), Group(name="pytest_g2")
    a = _rect("a")
    g1.add(a)
    with pytest.raises(ValueError, match="remove_subobject"):
        g2.add(a)
    assert a.parent is g1
    assert g2.subobjects == []


def test_moving_object_between_parents_updates_both_trees():
    g1, g2 = Group(name="pytest_g1"), Group(name="pytest_g2")
    a = _rect("a")
    g1.add(a)
    g1.remove_subobject(a)
    g2.add_subobject(a)
    assert g1.subobjects == []
    assert g2.subobjects == [a]
    assert a.parent is g2
    assert a.object.parent is g2.object
    g2.remove_subobject(a)
    assert g2.subobjects == []
    assert a.parent is None
    assert a.object.parent is None


def test_highlight_selects_descendants_and_clears_others():
    group = Group(name="pytest_group")
    a, b, other = _rect("a"), _rect("b"), _rect("other")
    group.add(a, b)
    other.object.select_set(True)

    group.highlight()
    assert all(o.object.select_get() for o in (group, a, b))
    assert not other.object.select_get()

    group.unhighlight()
    assert not any(o.object.select_get() for o in (group, a, b))


def test_joint_is_adopted_by_shared_parent_of_its_curves():
    from anima.primitives.joints import RoundJoint
    from anima.primitives.lines import Segment

    group = Group(name="pytest_group")
    c1, c2 = Segment((0, 0, 0), (1, 0, 0)), Segment((1, 0, 0), (1, 1, 0))
    group.add(c1, c2)
    joint = RoundJoint(c1, c2)
    assert joint.parent is group
    assert joint in group.subobjects
    assert joint not in c1.subobjects and joint not in c2.subobjects


def test_joint_without_shared_parent_stays_unparented():
    from anima.primitives.joints import RoundJoint
    from anima.primitives.lines import Segment

    c1, c2 = Segment((0, 0, 0), (1, 0, 0)), Segment((1, 0, 0), (1, 1, 0))
    joint = RoundJoint(c1, c2)
    assert joint.parent is None


def test_remove_subobject_detaches_child():
    group = Group(name="pytest_group")
    a, b = _rect("a"), _rect("b")
    group.add(a)
    with pytest.raises(ValueError):
        group.remove_subobject(b)
    group.remove_subobject(a)
    assert group.subobjects == []
    assert a.parent is None
    assert a.object.parent is None


def test_parent_is_read_only():
    group = Group(name="pytest_group")
    a = _rect("a")
    with pytest.raises(AttributeError):
        a.parent = group


def test_constructor_parent_registers_child():
    group = Group(name="pytest_group")
    child = Rectangle(1, 1, name="pytest_child", parent=group)
    assert group.subobjects == [child]
    assert child.object.parent is group.object


def test_tex_object_rejects_non_tex_child_via_constructor():
    from anima.latex.tex_object import TeXObject

    parent = TeXObject(name="pytest_tex")
    with pytest.raises(TypeError):
        Rectangle(1, 1, name="pytest_child", parent=parent)
