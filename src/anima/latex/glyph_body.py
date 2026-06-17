import json
from dataclasses import dataclass, replace

import numpy as np
import pytriwild as triwild

from anima.diagnostics import logger
from anima.globals.general import Vector
from anima.latex.glyph_border import GlyphBorder
from anima.primitives.bezier_curve import BezierCurve
from anima.primitives.mesh import Mesh
from anima.utils.geometry import compute_signed_area, flatten_cubic_bezier


@dataclass(frozen=True)
class MeshQuality:
    """Triangulation density/quality settings for a GlyphBody.

    The boundary of every glyph is flattened by Anima itself using a
    curvature-adaptive recursive subdivision of each Bezier curve (driven
    by `curve_tolerance`). The resulting polyline is handed to PyTriWild
    along with each Bezier curve's `feature_info`, where every adaptive
    sample appears as a feature `v_id`. This tags every boundary vertex
    as a feature point so PyTriWild's optimiser cannot collapse them
    while it works the interior.

    The default-constructed instance is the COARSEST useful preset,
    suitable for shader-driven looks (solid colours, paper textures,
    normal-mapped emboss/stamp). Use the presets, or override individual
    fields via `evolve(...)`.

    For glyph-shape silhouettes, only `curve_tolerance` matters - it
    directly controls how closely the boundary polyline tracks the true
    Bezier outline at high-curvature regions. The remaining knobs only
    affect the INTERIOR triangulation, which is invisible under flat
    shading / per-pixel materials.

    Attributes:
        curve_tolerance: Maximum chord-deviation (in input units) tolerated
            during Bezier flattening. Smaller -> more boundary vertices in
            high-curvature regions, sparse vertices on near-flat regions.
            This is the only knob that affects silhouette fidelity.
        boundary_envelope: PyTriWild `epsilon`. Hausdorff envelope around
            the input boundary used by the optimiser. Smaller values pin
            the boundary more rigidly during interior optimisation.
        relative_edge_length: PyTriWild `edge_length_ratio`. Target
            interior edge length, expressed as a fraction of the bbox
            diagonal. Larger -> coarser interior (fewer triangles).
        quality_threshold: PyTriWild `stop_quality` (AMIPS energy
            threshold). Larger -> permits worse-quality triangles,
            terminates sooner.
        max_iterations: PyTriWild `max_iterations`. Cap on optimisation
            passes.
    """

    curve_tolerance: float = 0.02
    boundary_envelope: float = 5e-2
    relative_edge_length: float = 0.5
    quality_threshold: float = 100.0
    max_iterations: int = 10

    @classmethod
    def minimal(cls) -> "MeshQuality":
        """Coarsest preset. Boundary stays smooth via adaptive flattening;
        interior is essentially a constrained Delaunay of the boundary
        points. Recommended default for flat-shaded, textured, or
        normal-mapped glyphs."""
        return cls()

    @classmethod
    def balanced(cls) -> "MeshQuality":
        """Moderate density. Useful for mild per-vertex effects or when
        you want some interior detail without paying the full HIGH cost."""
        return cls(
            curve_tolerance=0.005,
            boundary_envelope=5e-3,
            relative_edge_length=0.1,
            quality_threshold=20.0,
            max_iterations=40,
        )

    @classmethod
    def high(cls) -> "MeshQuality":
        """Dense, well-conditioned mesh. Use only when geometry is being
        deformed/displaced and per-vertex fidelity matters."""
        return cls(
            curve_tolerance=0.001,
            boundary_envelope=1e-3,
            relative_edge_length=0.02,
            quality_threshold=10.0,
            max_iterations=80,
        )

    def evolve(self, **overrides) -> "MeshQuality":
        """Return a copy of this preset with selected fields overridden.

        Example:
            MeshQuality.minimal().evolve(curve_tolerance=0.01)
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
            mesh_quality: Triangulation density/quality settings. Defaults to
                MeshQuality.minimal() (coarsest viable mesh).
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
        """Construct the triangulated mesh representing the glyph body.

        Boundary is flattened by Anima (curvature-adaptive); each Bezier
        becomes a feature whose `v_ids` enumerate every adaptive sample,
        so PyTriWild's optimiser is forbidden from collapsing them while
        it works the interior. This yields curvature-faithful boundaries
        with arbitrarily coarse interiors.
        """
        vertices, edges, feature_info, hole_points = self._border_to_triwild_input()
        q = self._mesh_quality

        result = triwild.triangulate(
            vertices,
            edges,
            feature_info=feature_info,
            cut_outside=True,
            hole_points=hole_points,
            mute_log=True,
            epsilon=q.boundary_envelope,
            edge_length_ratio=q.relative_edge_length,
            stop_quality=q.quality_threshold,
            max_iterations=q.max_iterations,
        )

        V_out = result[0]
        F_out = result[1]

        logger.trace(
            f"PyTriWild: {len(vertices)} input boundary verts -> {len(V_out)} output verts, {len(F_out)} faces"
        )

        self._vertices = [Vector((v[0], v[1], 0.0)) for v in V_out]
        self._faces = [tuple(f) for f in F_out]

        self.set_mesh(self._vertices, self._faces)

    def _border_to_triwild_input(
        self,
    ) -> tuple[np.ndarray, np.ndarray, str, np.ndarray]:
        """Convert GlyphBorder to PyTriWild input with curve features.

        Each cubic Bezier in the border is adaptively flattened using the
        `curve_tolerance` from the active MeshQuality, and the resulting
        polyline becomes the constrained boundary. Each Bezier is also
        emitted as a `BezierCurve` entry in `feature_info` whose `v_ids`
        list ALL of its adaptive sample vertices (with their parameters),
        so that PyTriWild's optimiser tags every boundary vertex as a
        feature point and refuses to collapse them. Holes (CW subpaths)
        get an interior point appended for PyTriWild's `hole_points`.

        Returns:
            vertices: (N, 2) float64 array of polyline points.
            edges: (M, 2) int32 array of segment connectivity (each row is
                a vertex-index pair).
            feature_info: JSON string encoding one feature per Bezier (or
                Line, for straight curves), keyed by `curve_id`.
            hole_points: (K, 2) float64 array of interior points marking
                holes to be carved out (one per CW subpath).
        """
        tolerance = self._mesh_quality.curve_tolerance

        all_vertices: list[tuple[float, float]] = []
        all_edges: list[tuple[int, int]] = []
        features: list[dict] = []
        hole_pts_list: list[list[float]] = []
        vertex_offset = 0
        curve_id = 0

        for subpath in self._border.subpaths:
            # Per-curve adaptive samples (points + their t-parameters)
            # alongside global vertex indices, for this whole subpath.
            curve_samples: list[tuple[type, list[tuple[float, float]], list[float], list[int]]] = []
            subpath_vertices: list[tuple[float, float]] = []

            for curve in subpath.curves:
                p0 = curve.spline_point(0).co
                p1 = curve.spline_point(1).co

                if isinstance(curve, BezierCurve):
                    h0 = curve._get_handle(side="RIGHT", point_index=0, relative=False)
                    h1 = curve._get_handle(side="LEFT", point_index=1, relative=False)
                    pts, ts = flatten_cubic_bezier(
                        (p0.x, p0.y),
                        (h0.x, h0.y),
                        (h1.x, h1.y),
                        (p1.x, p1.y),
                        tolerance,
                    )
                    poles = [
                        [p0.x, p0.y],
                        [h0.x, h0.y],
                        [h1.x, h1.y],
                        [p1.x, p1.y],
                    ]
                    curve_samples.append((BezierCurve, pts, ts, poles))
                else:
                    # Straight segment: a single sample at its start.
                    curve_samples.append((type(curve), [(p0.x, p0.y)], [0.0], None))

                subpath_vertices.extend(curve_samples[-1][1])

            num_verts = len(subpath_vertices)
            if num_verts < 3:
                continue

            area = compute_signed_area(subpath_vertices)
            if area < 0:
                centroid_x = sum(v[0] for v in subpath_vertices) / num_verts
                centroid_y = sum(v[1] for v in subpath_vertices) / num_verts
                hole_pts_list.append([centroid_x, centroid_y])
                logger.trace(f"Hole detected: area={area:.2f}, centroid=({centroid_x:.4f}, {centroid_y:.4f})")

            for i in range(num_verts):
                v0 = vertex_offset + i
                v1 = vertex_offset + ((i + 1) % num_verts)
                all_edges.append((v0, v1))

            # Emit one feature per curve. Each feature lists every sample
            # it owns AND the start-vertex of the next curve as its
            # closing v_id, so PyTriWild's BFS-based v_id-to-mesh mapping
            # can walk straight-line segments between consecutive samples.
            local_index = 0
            for _k, (cls, pts, ts, poles) in enumerate(curve_samples):
                start_idx = vertex_offset + local_index
                v_ids = [start_idx + j for j in range(len(pts))]
                next_first_idx = vertex_offset + ((local_index + len(pts)) % num_verts)
                v_ids.append(next_first_idx)
                paras = list(ts) + [1.0]

                if cls is BezierCurve:
                    features.append(
                        {
                            "type": "BezierCurve",
                            "curve_id": int(curve_id),
                            "v_ids": [int(v) for v in v_ids],
                            "paras": [float(t) for t in paras],
                            "degree": 3,
                            "poles": poles,
                        }
                    )
                else:
                    p_start = subpath_vertices[local_index]
                    p_end = subpath_vertices[(local_index + 1) % num_verts]
                    features.append(
                        {
                            "type": "Line",
                            "curve_id": int(curve_id),
                            "v_ids": [int(v) for v in v_ids],
                            "paras": [float(t) for t in paras],
                            "start": [p_start[0], p_start[1]],
                            "end": [p_end[0], p_end[1]],
                        }
                    )
                curve_id += 1
                local_index += len(pts)

            all_vertices.extend(subpath_vertices)
            vertex_offset += num_verts

        vertices = np.array(all_vertices, dtype=np.float64)
        edges = np.array(all_edges, dtype=np.int32) if all_edges else np.empty((0, 2), dtype=np.int32)
        hole_points = np.array(hole_pts_list, dtype=np.float64) if hole_pts_list else np.empty((0, 2), dtype=np.float64)
        feature_info = json.dumps(features) if features else None

        return vertices, edges, feature_info, hole_points
