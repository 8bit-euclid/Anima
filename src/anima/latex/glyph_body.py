from __future__ import annotations

import math
from dataclasses import dataclass, replace

import numpy as np

from anima.diagnostics import logger
from anima.globals.general import Vector
from anima.latex.glyph_border import GlyphBorder
from anima.latex.triangulation import DEFAULT_TRIANGULATOR, get_triangulator
from anima.primitives.bezier_curve import BezierCurve
from anima.primitives.mesh import Mesh
from anima.utils.geometry import compute_signed_area, flatten_cubic_bezier, point_in_polygon


@dataclass(frozen=True)
class MeshQuality:
    """Boundary resolution and triangulation backend for a GlyphBody.

    Every Bezier of the glyph border is flattened so that no segment turns the tangent by more than
    `max_turning_angle`: straight edges keep only their end points, corners keep a point, and curved regions get
    points in proportion to their curvature. The resulting polygon is triangulated without adding interior points,
    which is sufficient for flat-shaded or texture-driven looks.

    Attributes:
        max_turning_angle: Maximum tangent rotation per boundary segment, in degrees.
        triangulator: Name of the registered triangulation backend (see `anima.latex.triangulation`).
    """

    max_turning_angle: float = 10.0
    triangulator: str = DEFAULT_TRIANGULATOR

    @classmethod
    def minimal(cls) -> MeshQuality:
        """Coarsest preset. Recommended for flat-shaded, textured, or normal-mapped glyphs."""
        return cls(max_turning_angle=15.0)

    @classmethod
    def balanced(cls) -> MeshQuality:
        """Moderate boundary resolution."""
        return cls(max_turning_angle=7.0)

    @classmethod
    def high(cls) -> MeshQuality:
        """Fine boundary resolution for large or close-up glyphs."""
        return cls(max_turning_angle=3.0)

    def evolve(self, **overrides) -> MeshQuality:
        """Return a copy of this preset with selected fields overridden.

        Example:
            MeshQuality.minimal().evolve(triangulator="blender")
        """
        return replace(self, **overrides)


class GlyphBody(Mesh):
    def __init__(
        self,
        border: GlyphBorder,
        name: str = "GlyphBody",
        mesh_quality: MeshQuality | None = None,
    ):
        """Initialize a GlyphBody with a given GlyphBorder object.

        Args:
            border: A GlyphBorder object representing the border of the glyph.
            name: Name for this GlyphBody object.
            mesh_quality: Boundary resolution and triangulator. Defaults to MeshQuality.minimal().
        """
        self._border: GlyphBorder = border
        self._mesh_quality: MeshQuality = mesh_quality or MeshQuality.minimal()
        self._vertices: list[Vector] = []  # 2D vertices
        self._faces: list[tuple[int, int, int]] = []  # Triangular faces

        super().__init__(name=name)

        self._construct()

    @property
    def mesh_quality(self) -> MeshQuality:
        """The MeshQuality settings used to triangulate this body."""
        return self._mesh_quality

    def _construct(self):
        """Flatten the border, triangulate each outer contour with its holes, and build the mesh."""
        outers, owned = self._nest_contours(self._flatten_border())
        triangulator = get_triangulator(self._mesh_quality.triangulator)

        points: list[np.ndarray] = []
        faces: list[np.ndarray] = []
        offset = 0
        for outer, outer_holes in zip(outers, owned):
            faces.append(triangulator.triangulate(outer, outer_holes) + offset)
            rings = [outer, *outer_holes]
            points.extend(rings)
            offset += sum(len(r) for r in rings)

        if not points:
            return

        all_points = np.concatenate(points)
        all_faces = np.concatenate(faces)
        logger.trace(
            f"{triangulator.name}: {len(all_points)} boundary verts -> {len(all_faces)} faces "
            f"({len(outers)} outer contours)"
        )

        self._vertices = [Vector((x, y, 0.0)) for x, y in all_points]
        self._faces = [tuple(int(i) for i in f) for f in all_faces]
        self.set_mesh(self._vertices, self._faces)

    @staticmethod
    def _nest_contours(contours: list[np.ndarray]) -> tuple[list[np.ndarray], list[list[np.ndarray]]]:
        """Group contours into outer boundaries and their holes by nesting depth.

        A contour nested inside an even number of others is an outer boundary and one nested inside an odd number is
        a hole of its smallest enclosing contour. This is independent of winding direction.

        Returns:
            The outer contours and, for each, the list of its holes.
        """
        areas = [abs(compute_signed_area(c.tolist())) for c in contours]
        parents = [
            [j for j, other in enumerate(contours) if j != i and point_in_polygon(c[0], other)]
            for i, c in enumerate(contours)
        ]
        outer_index: dict[int, int] = {}
        outers: list[np.ndarray] = []
        holes: list[list[np.ndarray]] = []
        for i, enclosing in enumerate(parents):
            if len(enclosing) % 2 == 0:
                outer_index[i] = len(outers)
                outers.append(contours[i])
                holes.append([])
        for i, enclosing in enumerate(parents):
            if len(enclosing) % 2 == 1:
                parent = min(enclosing, key=areas.__getitem__)
                holes[outer_index[parent]].append(contours[i])
        return outers, holes

    def _flatten_border(self) -> list[np.ndarray]:
        """Flatten every border subpath into a polygon.

        Returns:
            One (N, 2) float array per subpath with at least three distinct vertices.
        """
        max_angle = math.radians(self._mesh_quality.max_turning_angle)
        contours: list[np.ndarray] = []

        for subpath in self._border.subpaths:
            pts: list[tuple[float, float]] = []
            for curve in subpath.curves:
                p0 = curve.spline_point(0).co
                if isinstance(curve, BezierCurve):
                    p1 = curve.spline_point(1).co
                    h0 = curve._get_handle(side="RIGHT", point_index=0, relative=False)
                    h1 = curve._get_handle(side="LEFT", point_index=1, relative=False)
                    pts.extend(flatten_cubic_bezier((p0.x, p0.y), (h0.x, h0.y), (h1.x, h1.y), (p1.x, p1.y), max_angle))
                else:
                    pts.append((p0.x, p0.y))

            polygon = np.array(pts, dtype=np.float64)
            # Drop consecutive duplicates (including the wrap-around one), which degenerate triangulation.
            keep = np.any(polygon != np.roll(polygon, 1, axis=0), axis=1)
            polygon = polygon[keep]
            if len(polygon) < 3:
                continue

            contours.append(polygon)

        return contours
