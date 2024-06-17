from general import *

MAX_SEGMENT_ANGLE_OFFSET = math.radians(75)


class SegmentChain:
    def __init__(self, vertices: List[Vector], width: float = 0.05, bias: float = 0.0,
                 angle_offs0: float = 0.0, angle_offs1: float = 0.0, intro: Interval = None,
                 outro: Interval = None, dimension=2):
        self.name = "Segment"
        self.obj = None
        self.dim = dimension

        # Note: currently only works for 2D but we resize to 3.
        self.vertices = [Vector(v).resized(3) for v in vertices]
        self.angle_offs0 = angle_offs0
        self.angle_offs1 = angle_offs1
        self.width = width
        assert -1.0 <= bias <= 1.0, \
            "The width bias must be in the range [-1.0, 1.0]."
        self.bias = bias
        self.segment_lengths = []
        self.total_length = 0.0

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
        half_width = 0.5 * self.width
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

            # Compute the end-direction at this vertex by applying the angle offset to the normal.
            direc = norm.copy()
            assert abs(angle_offs[i]) < MAX_SEGMENT_ANGLE_OFFSET, \
                "The offset angle is out of range."
            if angle_offs[i] != 0.0:
                eul = Euler((0.0, 0.0, angle_offs[i]), 'XYZ')
                direc.rotate(eul)

                # Normalise to have unit length orthogonal to the tangent.
                direc = direc / direc.dot(norm)

            # Position object vertices, considering end-directions, width, and bias.
            j = 4 * i  # Object vertex index
            v0 = verts[i] + (bias - 1.0) * half_width * direc
            v1 = verts[i] + (bias + 1.0) * half_width * direc
            if i > 0:
                obj_verts[j - 2].co = v0.copy()
                obj_verts[j - 1].co = v1.copy()
            if i < n_verts - 1:
                obj_verts[j + 0].co = v0.copy()
                obj_verts[j + 1].co = v1.copy()

    def _create_mesh(self):
        n_verts = len(self.vertices)

        obj_verts = []  # Note: different to the segment vertices
        obj_faces = []
        for i in range(n_verts - 1):
            for _ in range(4):  # 4 vertices per segment
                obj_verts.append((0, 0, 0))

            k = 4 * i  # Object vertex index
            obj_faces.append((k + 0, k + 1, k + 2))
            obj_faces.append((k + 1, k + 3, k + 2))

        # Create new bpy mesh and update base object.
        mesh = create_mesh("mesh", obj_verts, obj_faces)
        self.obj = add_object(self.name, mesh)

    def _make_intro(self):
        assert self.intro, "The intro animation interval was not set."
        assert self.obj, "The blender object has not been initialised."

        # Set load ratio keyframes.
        self.obj["load_ratio"] = 0.0
        self.obj.keyframe_insert(
            data_path='["load_ratio"]', frame=to_frame(self.intro.start))
        self.obj["load_ratio"] = 1.0
        self.obj.keyframe_insert(
            data_path='["load_ratio"]', frame=to_frame(self.intro.stop))

        # Set vertices 2 and 3 to be driven by the 'load_ratio'.
        total_len = self.total_length
        cumu_seg_len = 0.0
        for i in range(len(self.vertices) - 1):
            obj_verts = self.obj.data.vertices
            curr_seg_len = self.segment_lengths[i]

            a = cumu_seg_len / total_len
            b = curr_seg_len / total_len

            for j in [4*i + 2, 4*i + 3]:
                vert0 = obj_verts[j - 2].co
                vert1 = obj_verts[j].co

                # Get the drivers for the 3 vertex coordinates.
                drivers = add_driver(obj_verts[j], "co")
                for k, driver in enumerate(drivers):
                    # Linearly interpolate between the two vertices based on the 'load_ratio'.
                    driver_expr = f"{vert0[k]} if t < {a} else ({vert1[k]} if t > {a + b} else {vert0[k]} * (1 - (t - {a}) / {b}) + {vert1[k]} * (t - {a}) / {b})"

                    # Add driver script.
                    add_driver_script(driver, self.obj,
                                      '["load_ratio"]', 't', driver_expr)

            # Update cumulative segment length.
            cumu_seg_len += curr_seg_len

    def _make_outro(self):
        assert self.outro, "The outro animation interval was not set."
        assert self.obj, "The blender object has not been initialised."


class Segment(SegmentChain):
    def __init__(self, vert0: Vector, vert1: Vector, width: float = 0.05, bias: float = 0.0,
                 angle_offs0: float = 0.0, angle_offs1: float = 0.0, intro: Interval = None,
                 outro: Interval = None):
        super().__init__([vert0, vert1], width, bias,
                         angle_offs0, angle_offs1, intro, outro)
