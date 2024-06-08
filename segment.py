from general import *

MAX_SEGMENT_ANGLE_OFFSET = math.radians(75)


class SegmentChain:
    def __init__(self, vertices: List[Vector], thickness: float = 0.05, side_bias: float = 0.0,
                 angle_offs0: float = 0.0, angle_offs1: float = 0.0, intro: Interval = None,
                 outro: Interval = None, dimension=2):
        self.obj = None
        self.dim = dimension
        self.vertices = [Vector(v).resized(3) for v in vertices]
        self.angle_offs = [math.radians(ao)
                           for ao in [angle_offs0, angle_offs1]]
        self.thickness = thickness
        self.side_bias = side_bias
        self.intro = intro
        if self.intro:
            if not isinstance(intro, Interval):
                self.intro = Interval(*intro)
        self.outro = outro
        if self.outro:
            if not isinstance(outro, Interval):
                self.outro = Interval(*outro)

        # Create blender object
        self.obj = add_rectangle()

        # Build object
        self._build()

        # Create intro animation, if set.
        if self.intro:
            self._make_intro()

        # Create intro animation, if set.
        if self.outro:
            self._make_outro()

    def _build(self):
        verts = self.vertices
        angle_offs = self.angle_offs
        thickness = self.thickness
        side_bias = self.side_bias
        obj_verts = self.obj.data.vertices

        # Compute the normalised tangent of the segment.
        tang = verts[1] - verts[0]
        assert tang.length > 0.0, "A line must have non-zero length."
        tang = tang.normalized()

        # Compute the normal to the tangent.
        z_vect = Vector([0.0, 0.0, 1.0])
        norm = tang.cross(z_vect)

        for i in range(2):
            # Compute the end-direction at this vertex by applying the angle offset to the normal.
            direc = norm.copy()
            assert abs(
                angle_offs[i]) < MAX_SEGMENT_ANGLE_OFFSET, "Offset angle is out of range."
            if angle_offs[i] != 0.0:
                eul = Euler((0.0, 0.0, angle_offs[i]), 'XYZ')
                direc.rotate(eul)

                # Normalise to have unit length orthogonal to the tangent.
                direc = direc / direc.dot(norm)

            # Position object vertices, considering end-directions, thickness, and side bias.
            assert - \
                1.0 <= side_bias <= 1.0, "The side bias must be in range [-1.0, 1.0]."
            j = i + 2
            obj_verts[i].co = verts[i] + 0.5 * \
                (side_bias - 1.0) * thickness * direc
            obj_verts[j].co = verts[i] + 0.5 * \
                (side_bias + 1.0) * thickness * direc

    def _make_intro(self):
        assert self.intro, "The intro animation interval was not set."
        assert self.obj, "The blender object has not been initialised."

        # Set load factor keyframes.
        self.obj["load_factor"] = 0.0
        self.obj.keyframe_insert(
            data_path='["load_factor"]', frame=to_frame(self.intro.start))
        self.obj["load_factor"] = 1.0
        self.obj.keyframe_insert(
            data_path='["load_factor"]', frame=to_frame(self.intro.stop))

        obj_verts = self.obj.data.vertices

        # Set vertices 1 and 3 to be driven by the 'load_factor'.
        for i in [1, 3]:
            vert0 = obj_verts[i - 1].co
            vert1 = obj_verts[i].co

            # Get the drivers for the 3 vertex coordinates.
            drivers = add_driver(obj_verts[i], "co")
            for j, driver in enumerate(drivers):
                # Create a linear expression based on the 'load_factor'.
                add_driver_script(driver, self.obj, '["load_factor"]', 't',
                                  f"({vert0[j]} * (1 - t) + {vert1[j]} * t)")

    def _make_outro(self):
        assert self.outro, "The outro animation interval was not set."
        assert self.obj, "The blender object has not been initialised."


class Segment(SegmentChain):
    def __init__(self, vert0: Vector, vert1: Vector, thickness: float = 0.05, side_bias: float = 0.0,
                 angle_offs0: float = 0.0, angle_offs1: float = 0.0, intro: Interval = None,
                 outro: Interval = None):
        super().__init__([vert0, vert1], thickness,
                         side_bias, angle_offs0, angle_offs1, intro, outro)
