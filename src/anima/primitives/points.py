import bpy

from anima.globals.general import *
from anima.primitives.curves import DEFAULT_LINE_WIDTH
from anima.primitives.object import Object

DEFAULT_POINT_RADIUS = 1.1 * DEFAULT_LINE_WIDTH


class Empty(Object):
    """
    A data-less Blender empty with just a location. It is invisible in the final render and can be used as
    a reference point for other geometry, a hook that drives some object property, or a holder of custom
    properties (e.g. animated driver values).
    """

    def __init__(self, location=(0, 0, 0), parent=None, name="Empty"):
        obj = add_empty(name)
        super().__init__(bl_object=obj, name=name, parent=parent)
        self.location = make_3d_vector(location)


class Point(Object):
    """
    A point object that is visible in both the viewport and the render.
    """

    def __init__(self, location=(0, 0, 0), radius=DEFAULT_POINT_RADIUS, parent=None, name="Point"):
        # Normalize location to 3D (required for Blender's primitive_circle_add)
        location = make_3d_vector(location)

        # Add a filled circle
        bpy.ops.mesh.primitive_circle_add(
            radius=radius,
            location=location,
            fill_type="NGON",  # Options: NOTHING, NGON, TRIANGLE_FAN
            vertices=32,
        )
        circle = bpy.context.object
        circle.name = name

        super().__init__(bl_object=circle, name=name, parent=parent)
        self.location = location
