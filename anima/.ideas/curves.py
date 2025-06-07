from anima.globals.general import *
from anima.primitives.object import Object
from anima.animation.action import Interval

MAX_SEGMENT_ANGLE_OFFSET = math.radians(75)
MIN_DETACHED_ANGLE_OFFSET = math.radians(30)


class Rectangle(Object):
    def __init__(self, width, height):
        self.obj = add_object("Rectangle")
        super().__init__(bl_object=self.obj, name="Rectangle")
        self.width = width
        self.height = height
        self.hook = []

        self._build()

    def animate(self):
        # Set load ratio keyframes.
        self.obj["R"] = 0.0
        self.obj.keyframe_insert(data_path='["R"]', frame=0)
        self.obj["R"] = 2.0
        self.obj.keyframe_insert(data_path='["R"]', frame=400)

        # Set current shape key value to be driven by the load ratio.
        i = 1
        hook = self.hook[i].object

        # for i in range(4):
        # hook = self.hook[i].object

        # def mod(i, v):
        #     # hook.location[i] = 0.0
        #     hook.keyframe_insert(data_path="location", index=i, frame=0)
        #     hook.location[i] += v
        #     hook.keyframe_insert(data_path="location", index=i, frame=400)

        # if i == 0:
        #     mod(1, -1)
        # elif i == 1:
        #     mod(0, 1)
        # elif i == 2:
        #     mod(0, -1)
        # elif i == 3:
        #     mod(1, 1)

    def _create_mesh(self):
        obj_verts = []
        obj_faces = []
        obj_verts.append((0, 0, 0))
        obj_verts.append((1, 0, 0))
        obj_verts.append((0, 1, 0))
        obj_verts.append((1, 1, 0))

        obj_faces.append((0, 1, 2))
        obj_faces.append((1, 3, 2))

        # Create new bpy mesh and update base object.
        self.obj.data = create_mesh("mesh", obj_verts, obj_faces)

    def _build(self):
        self._create_mesh()

        for i in range(4):
            self.hook.append(add_empty_hook(f'v{i}', self.obj, i))

# region Segments


class SegmentChain:
    """
    This forms the basis for all curves and compund objects constructed from curves. 
    It is currently specialised for 2D curves only.
    """

    def __init__(self, vertices: list[Vector], width: float = 0.05, bias: float = 0.0,
                 angle_offs0: float = 0.0, angle_offs1: float = 0.0, intro: Interval = None,
                 outro: Interval = None, dimension=2, name='SegmentChain'):
        self.obj = add_object(name)
        self.name = name
        self.dim = dimension

        # Note: currently only works for 2D but we resize to 3.
        self.vertices = [
            add_empty(name=f'{name}.V{i}', location=Vector(v).resized(3), parent=self.obj) for i, v in enumerate(vertices)]
        self.angle_offs0 = angle_offs0
        self.angle_offs1 = angle_offs1
        self.width = width
        assert -1.0 <= bias <= 1.0, \
            "The width bias must be in the range [-1.0, 1.0]."
        self.bias = bias

        # Build object
        self._build()

        # Create intro animation, if set.
        if intro:
            self.intro = intro
            if not isinstance(intro, Interval):
                self.intro = Interval(*intro)
            self._make_intro()

        # Create outro animation, if set.
        if outro:
            self.outro = outro
            if not isinstance(outro, Interval):
                self.outro = Interval(*outro)
            self._make_outro()

    def _build(self):
        self._create_mesh()
        verts = self.vertices
        bias = self.bias
        obj_verts = self.obj.data.vertices

        # Compute offset angles at each vertex.
        n_verts = len(verts)
        angle_offs = []
        angle_offs.append(self.angle_offs0)  # First vertex.
        for i in range(1, n_verts - 1):  # Intermediate vertices.
            # Compute tangents.
            assert_2d(self.dim)
            tang_prev = (verts[i] - verts[i - 1]).resized(2)
            tang_curr = (verts[i + 1] - verts[i]).resized(2)
            # Compute signed angle. Note: 'angle_signed' treats CW as +ve. We want CCW as +ve.
            angle_offs.append(-0.5 * tang_prev.angle_signed(tang_curr))
        angle_offs.append(self.angle_offs1)  # Last vertex.

        self.segment_lengths = []
        self.total_length = 0.0

        for i in range(n_verts):
            # Compute the normalised tangent of the segment and update total length.
            tang = verts[i] - verts[i - 1] if i != 0 else verts[1] - verts[0]
            assert tang.length > 0.0, "A segment must have non-zero length."
            if i != 0:
                self.segment_lengths.append(tang.length)
                self.total_length += tang.length
            tang = tang.normalized()

            # Compute the normal to the tangent.
            assert_2d(self.dim)
            norm = tang.cross(UnitZ)

            assert abs(angle_offs[i]) < MAX_SEGMENT_ANGLE_OFFSET, \
                "The offset angle is out of range."

            # Compute the end-direction at this vertex by applying the angle offset to the normal.
            direc = norm.copy()
            if angle_offs[i] != 0.0:
                eul = Euler((0.0, 0.0, angle_offs[i]), 'XYZ')
                direc.rotate(eul)

                # Normalise to have unit length along the normal direction.
                direc = direc / direc.dot(norm)

            # Position object vertices, considering end-directions, width, and bias.
            v0 = verts[i] + (bias - 1.0) * (0.5 * self.width) * direc
            v1 = verts[i] + (bias + 1.0) * (0.5 * self.width) * direc

            detached = 0 < i < (
                n_verts - 1) and abs(angle_offs[i]) >= MIN_DETACHED_ANGLE_OFFSET
            if detached:
                # Compute next tangent and normalise in the same manner as for direc.
                tang2 = verts[i + 1] - verts[i]
                tang2 = -tang2 / tang2.dot(norm)
                v2 = v1 + self.width * tang2

            j = 4 * i  # Object vertex index
            if i > 0:
                obj_verts[j - 2].co = v2.copy() if detached else v0.copy()
                obj_verts[j - 1].co = v1.copy()
            if i < n_verts - 1:
                obj_verts[j + 0].co = v0.copy()
                obj_verts[j + 1].co = v2.copy() if detached else v1.copy()

    def _create_mesh(self):
        obj_verts = []  # Note: different to the segment vertices
        obj_faces = []
        for i in range(len(self.vertices) - 1):
            for _ in range(4):  # 4 vertices per segment
                obj_verts.append((0, 0, 0))

            k = 4 * i  # Object vertex index
            obj_faces.append((k + 0, k + 1, k + 2))
            obj_faces.append((k + 1, k + 3, k + 2))

        # Create new bpy mesh and update base object.
        self.obj.data = create_mesh("mesh", obj_verts, obj_faces)

    def _make_intro(self):
        assert self.intro, "The intro animation interval was not set."

        # Set load ratio keyframes.
        self.obj["load_ratio"] = 0.0
        self.obj.keyframe_insert(
            data_path='["load_ratio"]', frame=to_frame(self.intro.start))
        self.obj["load_ratio"] = 1.0
        self.obj.keyframe_insert(
            data_path='["load_ratio"]', frame=to_frame(self.intro.stop))

        # Set vertices 2 and 3 of each segment to be driven by the 'load_ratio'.
        obj_verts = self.obj.data.vertices
        total_len = self.total_length
        cumu_seg_len = 0.0
        shape_key_basis = self.obj.shape_key_add(name="Basis")
        shape_keys = []
        for i in range(len(self.vertices) - 1):
            curr_seg_len = self.segment_lengths[i]

            a = cumu_seg_len / total_len
            b = curr_seg_len / total_len

            # Create new shape key for this segment and add to list.
            shape_key = self.obj.shape_key_add(name=f"Loaded_{i}")
            shape_keys.append(shape_key)

            # Set shape key vertices.
            for j in [4*i + 2, 4*i + 3]:
                shape_key_basis.data[j].co = obj_verts[j - 2].co

                for sk in shape_keys:
                    sk.data[j].co = obj_verts[j - 2].co
                shape_key.data[j].co = obj_verts[j].co

            # Update cumulative segment length.
            cumu_seg_len += curr_seg_len

    def _make_outro(self):
        assert self.outro, "The outro animation interval was not set."
        assert self.obj, "The blender object has not been initialised."

        # Set load ratio keyframes.
        self.obj["load_ratio"] = 1.0
        self.obj.keyframe_insert(
            data_path='["load_ratio"]', frame=to_frame(self.outro.start))
        self.obj["load_ratio"] = 0.0
        self.obj.keyframe_insert(
            data_path='["load_ratio"]', frame=to_frame(self.outro.stop))


class Segment(SegmentChain):
    def __init__(self, vert0: Vector, vert1: Vector, width: float = 0.05, bias: float = 0.0,
                 angle_offs0: float = 0.0, angle_offs1: float = 0.0, intro: Interval = None,
                 outro: Interval = None, name='Segment'):

        super().__init__(vertices=[vert0, vert1],
                         width=width,
                         bias=bias,
                         angle_offs0=angle_offs0,
                         angle_offs1=angle_offs1,
                         intro=intro,
                         outro=outro,
                         name=name)
# endregion


# region Polygons
class Polygon(SegmentChain):
    def __init__(self, n_verts: int, width: float = 0.05, bias: float = 0.0,
                 angle_offs0: float = 0.0, angle_offs1: float = 0.0, intro: Interval = None,
                 outro: Interval = None, name='Polygon'):
        assert n_verts > 2, "A polygon must have at least 3 vertices."
        pass
# endregion


# region Curves
class ParametricCurve(SegmentChain):
    def __init__(self, point_func, param0: float, param1: float, width: float = 0.05, bias: float = 0.0,
                 angle_offs0: float = 0.0, angle_offs1: float = 0.0, intro: Interval = None,
                 outro: Interval = None, n_subdiv: int = 200, name='Curve'):

        # Compute vertices at each subdivision.
        verts = []
        n_verts = n_subdiv + 1
        delta = (param1 - param0) / n_subdiv
        param = param0
        for _ in range(n_verts):
            vert = point_func(param)
            verts.append(vert)
            param += delta

        super().__init__(vertices=verts,
                         width=width,
                         bias=bias,
                         angle_offs0=angle_offs0,
                         angle_offs1=angle_offs1,
                         intro=intro,
                         outro=outro,
                         name=name)


class EllipticalArc(ParametricCurve):
    def __init__(self, centre: Vector, radius_x: float, radius_y: float, theta0: float, theta1: float,
                 width: float = 0.05, bias: float = 0.0, angle_offs0: float = 0.0, angle_offs1: float = 0.0,
                 intro: Interval = None, outro: Interval = None, name='EllipticalArc'):

        self.centre = Vector(centre).resized(3)
        assert radius_x > 0.0 and radius_y > 0.0
        assert theta1 > theta0
        self.radius_x = radius_x
        self.radius_y = radius_y

        def point(t) -> Vector:
            return self.centre + Vector([radius_x * math.cos(t), radius_y * math.sin(t), 0.0])

        super().__init__(point_func=point,
                         param0=theta0,
                         param1=theta1,
                         width=width,
                         bias=bias,
                         angle_offs0=angle_offs0,
                         angle_offs1=angle_offs1,
                         intro=intro,
                         outro=outro,
                         name=name)


class Ellipse(EllipticalArc):
    def __init__(self, centre: Vector, radius_x: float, radius_y: float, width: float = 0.05,
                 bias: float = 0.0, intro: Interval = None, outro: Interval = None, name='Ellipse'):

        super().__init__(centre=centre,
                         radius_x=radius_x,
                         radius_y=radius_y,
                         theta0=0.0,
                         theta1=2.0*math.pi,
                         width=width,
                         bias=bias,
                         angle_offs0=0.0,
                         angle_offs1=0.0,
                         intro=intro,
                         outro=outro,
                         name=name)


class CircularArc(EllipticalArc):
    def __init__(self, centre: Vector, radius: float, theta0: float, theta1: float,
                 width: float = 0.05, bias: float = 0.0, angle_offs0: float = 0.0, angle_offs1: float = 0.0,
                 intro: Interval = None, outro: Interval = None, name='CircularArc'):

        super().__init__(centre=centre,
                         radius_x=radius,
                         radius_y=radius,
                         theta0=theta0,
                         theta1=theta1,
                         width=width,
                         bias=bias,
                         angle_offs0=angle_offs0,
                         angle_offs1=angle_offs1,
                         intro=intro,
                         outro=outro,
                         name=name)


class Circle(CircularArc):
    def __init__(self, centre: Vector, radius: float, width: float = 0.05,
                 bias: float = 0.0, intro: Interval = None, outro: Interval = None, name='Circle'):

        super().__init__(centre=centre,
                         radius=radius,
                         theta0=0.0,
                         theta1=2.0*math.pi,
                         width=width,
                         bias=bias,
                         angle_offs0=0.0,
                         angle_offs1=0.0,
                         intro=intro,
                         outro=outro,
                         name=name)
# endregion
