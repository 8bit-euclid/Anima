import math

import bpy

from anima.globals.general import Vector, add_object, create_mesh
from anima.primitives.mesh import Mesh

from .attachments import Attachment
from .curves import DEFAULT_LINE_WIDTH
from .points import DEFAULT_POINT_RADIUS

DEFAULT_ARROW_WIDTH = 3.5 * DEFAULT_LINE_WIDTH
DEFAULT_ARROW_HEIGHT_1 = 4 * DEFAULT_LINE_WIDTH
DEFAULT_ARROW_HEIGHT_2 = 0.4 * DEFAULT_LINE_WIDTH


class Endcap(Attachment):
    """Base class for endcaps that can be attached to curves.

    Subclasses should use multiple inheritance to compose the visual geometry
    (e.g., Mesh, Point) with the Attachment behavior. This follows the same
    pattern as Joint(Attachment, Curve, Mesh).
    """

    pass


class PointEndcap(Endcap, Mesh):
    """An endcap that represents a point at the end of a curve.

    Creates a filled circle mesh similar to Point, but follows the Endcap
    multiple inheritance pattern for proper composite hierarchy.
    """

    def __init__(self, radius=DEFAULT_POINT_RADIUS, name="PointEndcap"):
        # Create a filled circle mesh (same as Point)
        bpy.ops.mesh.primitive_circle_add(
            radius=radius,
            location=(0, 0, 0),
            fill_type="NGON",
            vertices=32,
        )
        bl_obj = bpy.context.object
        bl_obj.name = name

        super().__init__(bl_object=bl_obj, name=name)

    def offset_distance(self):
        return 0.0


class RoundEndcap(Endcap, Mesh):
    """An endcap that represents a rounded end at the end of a curve."""

    def __init__(
        self,
        width=DEFAULT_LINE_WIDTH,
        radius=0.5 * DEFAULT_LINE_WIDTH,
        name="RoundEndcap",
    ):
        assert 0 < 2 * radius <= width

        def quarter_circle_pts(center, start_angle, end_angle, segments):
            delta_angle = (end_angle - start_angle) / segments
            return [
                (
                    center.x + radius * math.cos(angle),
                    center.y + radius * math.sin(angle),
                    center.z,
                )
                for angle in [start_angle + i * delta_angle for i in range(segments + 1)]
            ]

        half_width = 0.5 * width
        c1 = Vector((half_width - radius, 0, 0))
        c2 = -c1

        num_segs = 8
        circle_1 = quarter_circle_pts(c1, 0.0, 0.5 * math.pi, num_segs)
        circle_2 = quarter_circle_pts(c2, 0.5 * math.pi, math.pi, num_segs)

        # Create mesh and bl_object directly (no wrapper Mesh object).
        verts = circle_1 + circle_2
        faces = [list(range(2 * (num_segs + 1)))]
        mesh_data = create_mesh(f"{name}_mesh", verts, faces)
        bl_obj = add_object(name, mesh_data)

        super().__init__(bl_object=bl_obj, name=name)
        self.unhide()

    def offset_distance(self):
        return 0.0


class ArrowEndcap(Endcap, Mesh):
    """An endcap that represents an arrow at the end of a curve."""

    def __init__(
        self,
        width=DEFAULT_ARROW_WIDTH,
        height_1=DEFAULT_ARROW_HEIGHT_1,
        height_2=DEFAULT_ARROW_HEIGHT_2,
        name="ArrowEndcap",
    ):
        # Store height_1 before super().__init__() for offset_distance().
        self.height_1 = height_1

        v3 = Vector((0, 0, 0))
        v1 = Vector((0, -height_1, 0))
        v2 = v1 + Vector((0.5 * width, -height_2, 0))
        v4 = v2.copy()
        v4.x *= -1.0

        # Create mesh and bl_object directly (no wrapper Mesh object).
        verts = [v1, v2, v3, v4]
        faces = [[0, 1, 2, 3]]
        mesh_data = create_mesh(f"{name}_mesh", verts, faces)
        bl_obj = add_object(name, mesh_data)

        super().__init__(bl_object=bl_obj, name=name)
        self.unhide()

    def offset_distance(self):
        return self.height_1
