import json

import numpy as np
import pytriwild as triwild

from anima.diagnostics import logger
from anima.globals.general import Vector
from anima.latex.glyph_border import GlyphBorder
from anima.primitives.bezier_curve import BezierCurve
from anima.primitives.mesh import Mesh
from anima.utils.geometry import compute_signed_area


class GlyphBody(Mesh):
    def __init__(self, border: GlyphBorder, name: str = "GlyphBody"):
        """Initialize a GlyphBody with a given GlyphBorder object.

        Args:
            border: A GlyphBorder object representing the border of the glyph.
            name: Name for this GlyphBody object.
        """
        self._border: GlyphBorder = border
        self._vertices: list[Vector] = []  # 2D vertices
        self._faces: list[tuple[int, int, int]] = []  # Triangular faces

        super().__init__(name=name)

        self._construct()

    def _construct(self):
        """Construct the triangulated mesh representing the glyph body."""
        # Convert border to pytriwild input format
        vertices, feature_info, hole_points = self._border_to_triwild_input()

        # PyTriWild extracts edge connectivity from feature_info, so no explicit edges array needed
        empty_edges = np.empty((0, 2), dtype=np.int32)

        # Call pytriwild triangulation with curve constraints
        # cut_outside=True removes exterior triangles
        # hole_points specifies centroids of holes to be removed
        # mute_log=True disables PyTriWild's verbose output
        result = triwild.triangulate(
            vertices,
            empty_edges,
            feature_info=feature_info,
            cut_outside=True,
            hole_points=hole_points,
            mute_log=True,
        )

        # Extract vertices and faces from result tuple
        V_out = result[0]  # Output vertices (2D)
        F_out = result[1]  # Output faces

        logger.trace(f"PyTriWild triangulation: {len(V_out)} vertices, {len(F_out)} faces")

        # Store results - convert 2D vertices to 3D (z=0)
        self._vertices = [Vector((v[0], v[1], 0.0)) for v in V_out]
        self._faces = [tuple(f) for f in F_out]

        # Update mesh
        self.set_mesh(self._vertices, self._faces)

    def _border_to_triwild_input(self) -> tuple[np.ndarray, str, np.ndarray]:
        """Convert GlyphBorder to pytriwild input format.

        Returns:
            vertices: (n, 2) numpy array of 2D points
            feature_info: JSON string with Bezier curve data (includes connectivity via v_ids)
            hole_points: (k, 2) numpy array of points inside each hole (CW subpath)
        """
        all_vertices = []
        curve_to_vertex_map = {}
        hole_pts_list = []
        vertex_offset = 0

        # Process each subpath
        for subpath in self._border.subpaths:
            subpath_vertices = []

            # Extract vertices from each curve in the subpath
            for curve in subpath.curves:
                start_pt = curve.spline_point(0).co
                subpath_vertices.append((start_pt.x, start_pt.y))

            # Compute signed area to determine if this is a hole (CW winding)
            area = compute_signed_area(subpath_vertices)

            # If this is a hole (negative area = CW winding), compute its centroid
            if area < 0:
                centroid_x = sum(v[0] for v in subpath_vertices) / len(subpath_vertices)
                centroid_y = sum(v[1] for v in subpath_vertices) / len(subpath_vertices)
                hole_pts_list.append([centroid_x, centroid_y])
                logger.trace(f"Hole detected: area={area:.2f}, centroid=({centroid_x:.4f}, {centroid_y:.4f})")

            # Map curves to their vertex indices for feature_info construction
            num_verts = len(subpath_vertices)
            for i in range(num_verts):
                v0_idx = vertex_offset + i
                v1_idx = vertex_offset + ((i + 1) % num_verts)
                curve_to_vertex_map[len(curve_to_vertex_map)] = (subpath.curves[i], v0_idx, v1_idx)

            all_vertices.extend(subpath_vertices)
            vertex_offset += num_verts

        # Convert to numpy arrays
        vertices = np.array(all_vertices, dtype=np.float64)
        hole_points = np.array(hole_pts_list, dtype=np.float64) if hole_pts_list else np.empty((0, 2), dtype=np.float64)

        # Build feature info JSON string - contains both curve geometry and connectivity (v_ids)
        feature_info = self._build_feature_info(curve_to_vertex_map)

        return vertices, feature_info, hole_points

    def _build_feature_info(self, curve_to_vertex_map: dict) -> str:
        """Build feature info JSON string for all curves.

        PyTriWild uses feature_info to extract both curve geometry and edge connectivity.
        Each feature contains v_ids (vertex indices) for connectivity and poles (control points)
        for curve geometry.

        Args:
            curve_to_vertex_map: Dictionary mapping curve indices to (BezierCurve, v0_idx, v1_idx)

        Returns:
            JSON string containing Bezier curve feature information for pytriwild
        """
        features = []

        for curve_id, (curve, v0_idx, v1_idx) in curve_to_vertex_map.items():
            if isinstance(curve, BezierCurve):
                # Get control points (absolute positions)
                p0 = curve.spline_point(0).co
                p1 = curve.spline_point(1).co
                h0 = curve._get_handle(side="RIGHT", point_index=0, relative=False)
                h1 = curve._get_handle(side="LEFT", point_index=1, relative=False)

                features.append(
                    {
                        "type": "BezierCurve",
                        "curve_id": int(curve_id),
                        "v_ids": [int(v0_idx), int(v1_idx)],  # Connectivity information
                        "paras": [0.0, 1.0],
                        "degree": 3,
                        "poles": [[p0.x, p0.y], [h0.x, h0.y], [h1.x, h1.y], [p1.x, p1.y]],  # Curve geometry
                    }
                )

        return json.dumps(features)
