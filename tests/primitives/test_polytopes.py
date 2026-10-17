import bpy
import pytest

from anima.primitives.object import Object
from anima.primitives.polytopes import Polygon, Rectangle, Triangle


@pytest.fixture(autouse=True)
def cleanup_polytope_objects():
    yield
    for obj in list(bpy.data.objects):
        if obj.name.startswith("pytest_"):
            bpy.data.objects.remove(obj, do_unlink=True)


def test_polygon_builds_an_anima_mesh_object():
    polygon = Polygon(
        [(0, 0), (2, 0), (1, 1)],
        name="pytest_polygon",
        location=(1, 2, 3),
    )

    assert isinstance(polygon, Object)
    assert polygon.object.type == "MESH"
    assert len(polygon.vertices) == 3
    assert len(polygon.faces) == 1
    assert tuple(polygon.location) == pytest.approx((1, 2, 3))
    assert [tuple(vertex.co) for vertex in polygon.vertices] == [
        (0, 0, 0),
        (2, 0, 0),
        (1, 1, 0),
    ]


def test_triangle_requires_exactly_three_vertices():
    with pytest.raises(ValueError, match="exactly 3 vertices"):
        Triangle([(0, 0), (1, 0)])


def test_polygon_requires_at_least_three_vertices():
    with pytest.raises(ValueError, match="at least 3 vertices"):
        Polygon([(0, 0), (1, 0)])


def test_polygon_vertices_must_be_two_or_three_dimensional():
    with pytest.raises(ValueError, match="2 or 3 coordinates"):
        Polygon([(0,), (1, 0), (0, 1)])


def test_rectangle_builds_centered_dimensions_and_accepts_parent():
    parent = Object(name="pytest_parent")
    rectangle = Rectangle(20, 10, name="pytest_rectangle", parent=parent)

    assert isinstance(rectangle, Polygon)
    assert rectangle.parent is parent
    assert tuple(tuple(vertex.co) for vertex in rectangle.vertices) == (
        (-10, -5, 0),
        (10, -5, 0),
        (10, 5, 0),
        (-10, 5, 0),
    )
    assert len(rectangle.faces) == 1


@pytest.mark.parametrize(
    ("length", "width"),
    [(0, 1), (1, 0), (-1, 1), (1, -1)],
)
def test_rectangle_dimensions_must_be_positive(length, width):
    with pytest.raises(ValueError, match="must be greater than 0"):
        Rectangle(length, width)
