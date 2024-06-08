# region IMPORTS
from general import *

# endregion

# region SHAPE


class Shape:
    def __init__(self, dimension: int = 2):
        assert dimension in [2, 3], "Dimension can be either 2 or 3"
        self.dimension = dimension
        self.object = bpy.ops.object.empty_add()
        link_object(self.object)

    def update(self):
        raise NotImplementedError("The subclass must implement this method.")

    def animate(self):
        raise NotImplementedError("The subclass must implement this method.")
# endregion

# region LINE


class Line(Shape):
    def __init__(self, vert0: Vector, vert1: Vector, thickness: float, side_factor: float, dimension: int = 2):
        assert side_factor >= - \
            1.0 and side_factor <= 1.0, "The side factor should be in the [-1, 1] range."
        Shape.__init__(self, dimension)
        self.v0 = vert0
        self.v1 = vert1
        self.thickness = thickness
        self.side_factor = side_factor

    def update(self):
        pass
# endregion
