import math
from apeiron.globals.general import Vector
from .points import Empty, Point
from .curves import DEFAULT_LINE_WIDTH
from .attachments import BaseAttachment

DEFAULT_ARROW_WIDTH = 3.5 * DEFAULT_LINE_WIDTH
DEFAULT_ARROW_HEIGHT_1 = 4 * DEFAULT_LINE_WIDTH
DEFAULT_ARROW_HEIGHT_2 = 0.4 * DEFAULT_LINE_WIDTH


class Endcap(BaseAttachment):
    def __init__(self, obj, name='Endcap'):
        super().__init__(obj.object, name=name)


class PointEndcap(Endcap):
    def __init__(self, name='PointEndcap'):
        super().__init__(Point(), name=name)

    def offset_distance(self):
        return 0.0


class RoundEndcap(Endcap):
    def __init__(self, width=DEFAULT_LINE_WIDTH, radius=0.5*DEFAULT_LINE_WIDTH, name='RoundEndcap'):
        assert 0 < 2*radius <= width

        def quarter_circle_pts(center, start_angle, end_angle, segments):
            delta_angle = (end_angle - start_angle) / segments
            return [
                (center.x + radius * math.cos(angle),
                 center.y + radius * math.sin(angle),
                 center.z)
                for angle in [start_angle + i * delta_angle for i in range(segments + 1)]
            ]

        half_width = 0.5 * width
        c1 = Vector((half_width - radius, 0, 0))
        c2 = -c1

        num_segs = 8
        circle_1 = quarter_circle_pts(c1, 0.0, 0.5*math.pi, num_segs)
        circle_2 = quarter_circle_pts(c2, 0.5*math.pi, math.pi, num_segs)

        obj = Empty(name=name)
        obj.set_mesh(verts=circle_1 + circle_2,
                     faces=[range(2*(num_segs + 1))])
        obj.unhide()

        super().__init__(obj, name=name)

    def offset_distance(self):
        return 0.0


class ArrowEndcap(Endcap):
    def __init__(self, width=DEFAULT_ARROW_WIDTH, height_1=DEFAULT_ARROW_HEIGHT_1,
                 height_2=DEFAULT_ARROW_HEIGHT_2, name='ArrowEndcap'):
        self.height_1 = height_1

        obj = Empty(name=name)

        v3 = Vector((0, 0, 0))
        v1 = Vector((0, -height_1, 0))
        v2 = v1 + Vector((0.5*width, -height_2, 0))
        v4 = v2.copy()
        v4.x *= -1.0
        obj.set_mesh(verts=[v1, v2, v3, v4], faces=[[0, 1, 2, 3]])
        obj.unhide()

        super().__init__(obj, name=name)

    def offset_distance(self):
        return self.height_1
