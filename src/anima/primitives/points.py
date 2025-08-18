import bpy

from anima.globals.general import *
from anima.primitives.curves import DEFAULT_LINE_WIDTH
from anima.primitives.object import Object

DEFAULT_POINT_RADIUS = 1.1 * DEFAULT_LINE_WIDTH


class Empty(Object):
    """
    An object with just a point location and no mesh. It is invisible in the final render and can be used as
    reference points for other geometry or as a hook that drives some object property.
    """

    def __init__(self, location=(0, 0, 0), parent=None, name="Empty"):
        mesh = create_mesh(f"{name}_mesh", verts=[(0, 0, 0)], faces=[])
        obj = add_object(name, mesh, parent=parent)

        super().__init__(bl_object=obj, name=name)
        self.location = location
        if parent is not None:
            self.parent = parent


class Point(Object):
    """
    A point object that is visible in both the viewport and the render.
    """

    def __init__(
        self, location=(0, 0, 0), radius=DEFAULT_POINT_RADIUS, parent=None, name="Point"
    ):
        # Add a filled circle
        bpy.ops.mesh.primitive_circle_add(
            radius=radius,
            location=location,
            fill_type="NGON",  # Options: NOTHING, NGON, TRIANGLE_FAN
            vertices=32,
        )
        circle = bpy.context.object
        circle.name = name

        super().__init__(bl_object=circle, name=name)
        self.location = location
        if parent is not None:
            self.parent = parent
