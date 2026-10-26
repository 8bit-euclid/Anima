import bpy
import pytest

from anima.globals.general import LAYER_SPACING
from anima.primitives.object import Object


@pytest.fixture(autouse=True)
def cleanup_layer_objects():
    yield
    for obj in list(bpy.data.objects):
        if obj.name.startswith("pytest_"):
            bpy.data.objects.remove(obj, do_unlink=True)


def test_layer_defaults_to_zero():
    obj = Object(name="pytest_layer_default")
    assert obj.layer == 0
    assert obj.object.delta_location.z == 0


def test_layer_sets_delta_location_without_touching_location():
    obj = Object(name="pytest_layer_obj")
    obj.location = (1, 2, 3)
    obj.layer = 2

    assert obj.layer == 2
    assert obj.object.delta_location.z == pytest.approx(2 * LAYER_SPACING)
    assert tuple(obj.location) == pytest.approx((1, 2, 3))

    obj.layer = 0
    assert obj.object.delta_location.z == 0


def test_layer_is_copied_with_the_object():
    obj = Object(name="pytest_layer_copy")
    obj.layer = 3
    copy = obj.copy()
    copy.name = "pytest_layer_copy_2"

    assert copy.layer == 3
    assert copy.object.delta_location.z == pytest.approx(3 * LAYER_SPACING)


def test_child_layer_adds_to_parent_layer_in_world_space():
    parent = Object(name="pytest_layer_parent")
    child = Object(name="pytest_layer_child")
    parent.add_child(child)
    parent.layer = 1
    child.layer = 2
    bpy.context.view_layer.update()

    assert child.object.matrix_world.translation.z == pytest.approx(3 * LAYER_SPACING)
    assert child.object.delta_location.z == pytest.approx(2 * LAYER_SPACING)
