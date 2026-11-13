"""Tests for Group, parenting rules and viewport highlighting."""

import bpy
import pytest

from anima.primitives.bezier_spline import BezierSpline
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


def test_visibility_skips_unchanged_writes_but_honors_external_changes(monkeypatch):
    class VisibilitySpy:
        def __init__(self):
            self.writes = []
            self.hide_viewport = False
            self.hide_render = False
            self.writes.clear()

        def __setattr__(self, name, value):
            if name in ("hide_viewport", "hide_render"):
                self.writes.append((name, value))
            super().__setattr__(name, value)

    group = Group(name="pytest_group")
    spy = VisibilitySpy()
    monkeypatch.setattr(group, "_bl_object", spy)
    group.unhide()
    assert spy.writes == []
    group.hide()
    assert spy.writes == [("hide_viewport", True), ("hide_render", True)]
    spy.writes.clear()
    spy.hide_viewport = False
    spy.writes.clear()
    group.hide()
    assert spy.writes == [("hide_viewport", True)]


def test_visibility_recurses_when_parent_already_has_requested_state():
    group = Group(name="pytest_group")
    child = _rect("child")
    group.add(child)
    group.hide()
    child.object.hide_viewport = False
    child.object.hide_render = False
    group.hide()
    assert child.object.hide_viewport and child.object.hide_render
    group.unhide()
    assert not group.object.hide_viewport and not group.object.hide_render
    assert not child.object.hide_viewport and not child.object.hide_render


def test_add_child_is_idempotent_for_same_parent():
    group = Group(name="pytest_group")
    a = _rect("a")
    group.add(a, a)
    group.add_child(a)
    assert group.children == [a]


def test_adding_to_a_second_parent_raises():
    g1, g2 = Group(name="pytest_g1"), Group(name="pytest_g2")
    a = _rect("a")
    g1.add(a)
    with pytest.raises(ValueError, match="remove_child"):
        g2.add(a)
    assert a.parent is g1
    assert g2.children == []


def test_moving_object_between_parents_updates_both_trees():
    g1, g2 = Group(name="pytest_g1"), Group(name="pytest_g2")
    a = _rect("a")
    g1.add(a)
    g1.remove_child(a)
    g2.add_child(a)
    assert g1.children == []
    assert g2.children == [a]
    assert a.parent is g2
    assert a.object.parent is g2.object
    g2.remove_child(a)
    assert g2.children == []
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
    assert joint in group.children
    assert joint not in c1.children and joint not in c2.children


def test_joint_without_shared_parent_stays_unparented():
    from anima.primitives.joints import RoundJoint
    from anima.primitives.lines import Segment

    c1, c2 = Segment((0, 0, 0), (1, 0, 0)), Segment((1, 0, 0), (1, 1, 0))
    joint = RoundJoint(c1, c2)
    assert joint.parent is None


def test_remove_child_detaches_child():
    group = Group(name="pytest_group")
    a, b = _rect("a"), _rect("b")
    group.add(a)
    with pytest.raises(ValueError):
        group.remove_child(b)
    group.remove_child(a)
    assert group.children == []
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
    assert group.children == [child]
    assert child.object.parent is group.object


def test_copy_preserves_material_sharing_within_hierarchy_but_not_with_original():
    a, b = _rect("a"), _rect("b")
    shared = bpy.data.materials.new("pytest_shared")
    shared.node_tree.nodes.remove(shared.node_tree.nodes["Principled BSDF"])
    shared.diffuse_color = (1, 0, 0, 1)
    a.object.data.materials.append(shared)
    b.object.data.materials.append(shared)
    group = Group([a, b], name="pytest_group")

    copied = group.copy()
    copied_a, copied_b = copied.children
    copied_material = copied_a.object.data.materials[0]
    assert copied_material != shared
    assert copied_material == copied_b.object.data.materials[0]
    assert copied_a.parent is copied
    assert copied_a.object.parent == copied.object
    copied_a.set_color((0.0, 0.0, 1.0, 0.5))
    assert copied_b.color == pytest.approx((0, 0, 1, 0.5))
    assert a.color == pytest.approx((1, 0, 0, 1))
    b.set_color((0.0, 1.0, 0.0, 1.0))
    assert copied_a.color == pytest.approx((0, 0, 1, 0.5))

    another_copy = group.copy()
    assert another_copy.children[0].object.data.materials[0] != copied_material
    assert another_copy.children[0].object.data.materials[0] != shared


def test_copy_preserves_multiple_data_and_object_material_slots():
    rect = _rect("slots")
    data_material = bpy.data.materials.new("pytest_data")
    object_material = bpy.data.materials.new("pytest_object")
    rect.object.data.materials.append(data_material)
    rect.object.data.materials.append(data_material)
    rect.object.data.materials.append(None)
    rect.object.data.materials.append(data_material)
    rect.object.data.materials.append(None)
    rect.object.material_slots[0].link = "OBJECT"
    rect.object.material_slots[0].material = object_material
    rect.object.material_slots[3].link = "OBJECT"
    rect.object.material_slots[3].material = data_material
    rect.object.material_slots[4].link = "OBJECT"

    copied = rect.copy()
    data = copied.object.data.materials
    slots = copied.object.material_slots
    assert [slot.link for slot in slots] == ["OBJECT", "DATA", "DATA", "OBJECT", "OBJECT"]
    assert data[0] == data[1] == data[3] != data_material
    assert data[2] is None
    assert slots[0].material != object_material
    assert slots[1].material == slots[3].material == data[0]
    assert slots[2].material is None
    assert slots[4].material is None
    slots[0].material.diffuse_color = (0, 0, 1, 1)
    assert tuple(object_material.diffuse_color) != pytest.approx((0, 0, 1, 1))


def test_copy_spline_profile_shares_copied_material_with_spline():
    spline = BezierSpline([(0, 0), (1, 1)], name="pytest_spline")
    spline.set_color((1.0, 0.0, 0.0, 1.0))
    material = spline.object.data.materials[0]
    profile = spline.object.data.bevel_object
    profile.data.materials.append(material)

    copied = spline.copy()
    copied_profile = copied.object.data.bevel_object
    assert copied_profile != profile
    assert copied_profile.parent == copied.object
    assert copied_profile.data.materials[0] == copied.object.data.materials[0] != material


def test_copy_material_animation_actions_are_independent():
    rect = _rect("animated")
    rect.set_color((1.0, 0.0, 0.0, 1.0))
    material = rect.object.data.materials[0]
    material.keyframe_insert(data_path="diffuse_color", frame=1)
    node_tree = material.node_tree
    alpha = node_tree.nodes["Principled BSDF"].inputs["Alpha"]
    alpha.keyframe_insert(data_path="default_value", frame=1)
    node_action = node_tree.animation_data.action
    node_tree.animation_data.action = None
    track = node_tree.animation_data.nla_tracks.new()
    track.strips.new("alpha", 1, node_action)
    node_tree.animation_data.action = node_action

    copied = rect.copy()
    copied_material = copied.object.data.materials[0]
    copied_tree = copied_material.node_tree
    assert copied_material.animation_data.action != material.animation_data.action
    copied_action = copied_tree.animation_data.action
    assert copied_action != node_action
    assert copied_tree.animation_data.nla_tracks[0].strips[0].action == copied_action
    copied_material.diffuse_color = (0, 0, 1, 1)
    copied_material.keyframe_insert(data_path="diffuse_color", frame=3)
    assert tuple(material.animation_data.action.frame_range) == pytest.approx((1, 1))
    assert tuple(copied_material.animation_data.action.frame_range) == pytest.approx((1, 3))
    copied_alpha = copied_tree.nodes["Principled BSDF"].inputs["Alpha"]
    copied_alpha.keyframe_insert(data_path="default_value", frame=4)
    assert tuple(node_action.frame_range) == pytest.approx((1, 1))
    assert tuple(copied_action.frame_range) == pytest.approx((1, 4))
    scene = bpy.context.scene
    frame = scene.frame_current
    try:
        scene.frame_set(3)
        assert tuple(material.diffuse_color) == pytest.approx((1, 0, 0, 1))
        assert tuple(copied_material.diffuse_color) == pytest.approx((0, 0, 1, 1))
    finally:
        scene.frame_set(frame)


def test_tex_object_rejects_non_tex_child_via_constructor():
    from anima.latex.tex_object import TeXObject

    parent = TeXObject(name="pytest_tex")
    with pytest.raises(TypeError):
        Rectangle(1, 1, name="pytest_child", parent=parent)
