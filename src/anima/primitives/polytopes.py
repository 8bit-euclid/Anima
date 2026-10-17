from collections.abc import Sequence

from mathutils import Vector

from anima.globals.general import make_3d_vector

from .mesh import Mesh
from .object import Object

_Vertex = Sequence[float] | Vector
_Vertices = Sequence[_Vertex]


class Polygon(Mesh):
    """A planar polygon represented by one mesh face."""

    def __init__(
        self,
        vertices: _Vertices,
        *,
        location: Sequence[float] = (0, 0, 0),
        name: str = "Polygon",
        parent: Object | None = None,
    ) -> None:
        """Initialize a polygon with the given vertices.

        Args:
            vertices (_Vertices): The vertices of the polygon.
            location (Sequence[float], optional): The location of the polygon. Defaults to (0, 0, 0).
            name (str, optional): The name of the polygon. Defaults to "Polygon".
            parent (Object | None, optional): The parent object. Defaults to None.
        """
        if len(vertices) < 3:
            raise ValueError("A polygon must have at least 3 vertices.")

        mesh_verts = []
        for vertex in vertices:
            if len(vertex) not in (2, 3):
                raise ValueError("Polygon vertices must have 2 or 3 coordinates.")
            mesh_verts.append(make_3d_vector(vertex))

        super().__init__(name=name, parent=parent)
        self.set_mesh(mesh_verts, [tuple(range(len(mesh_verts)))])
        self.location = location


class Triangle(Polygon):
    """A three-vertex polygon."""

    def __init__(
        self,
        vertices: _Vertices,
        *,
        location: Sequence[float] = (0, 0, 0),
        name: str = "Triangle",
        parent: Object | None = None,
    ) -> None:
        """Initialize a triangle with the given vertices.

        Args:
            vertices (_Vertices): The vertices of the triangle.
            location (Sequence[float], optional): The location of the triangle. Defaults to (0, 0, 0).
            name (str, optional): The name of the triangle. Defaults to "Triangle".
            parent (Object | None, optional): The parent object. Defaults to None.
        """
        if len(vertices) != 3:
            raise ValueError("A triangle must have exactly 3 vertices.")
        super().__init__(vertices, location=location, name=name, parent=parent)


class Rectangle(Polygon):
    """An axis-aligned rectangle centered at its local origin."""

    def __init__(
        self,
        length: float,
        width: float,
        *,
        location: Sequence[float] = (0, 0, 0),
        name: str = "Rectangle",
        parent: Object | None = None,
    ) -> None:
        """Initialize a rectangle with the given length and width.

        Args:
            length (float): The length of the rectangle.
            width (float): The width of the rectangle.
            location (Sequence[float], optional): The location of the rectangle. Defaults to (0, 0, 0).
            name (str, optional): The name of the rectangle. Defaults to "Rectangle".
            parent (Object | None, optional): The parent object. Defaults to None.
        """
        if length <= 0:
            raise ValueError("Rectangle length must be greater than 0.")
        if width <= 0:
            raise ValueError("Rectangle width must be greater than 0.")

        half_length = length / 2
        half_width = width / 2
        vertices = (
            (-half_length, -half_width),
            (half_length, -half_width),
            (half_length, half_width),
            (-half_length, half_width),
        )
        super().__init__(vertices, location=location, name=name, parent=parent)


class Square(Rectangle):
    """An axis-aligned square centered at its local origin."""

    def __init__(
        self,
        side: float,
        *,
        location: Sequence[float] = (0, 0, 0),
        name: str = "Square",
        parent: Object | None = None,
    ) -> None:
        """Initialize a square with the given side length.

        Args:
            side (float): The side length of the square.
            location (Sequence[float], optional): The location of the square. Defaults to (0, 0, 0).
            name (str, optional): The name of the square. Defaults to "Square".
            parent (Object | None, optional): The parent object. Defaults to None.
        """
        if side <= 0:
            raise ValueError("Square side length must be greater than 0.")
        super().__init__(length=side, width=side, location=location, name=name, parent=parent)
