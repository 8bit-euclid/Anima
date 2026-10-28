"""Unit tests for angle-based Bezier flattening and the glyph triangulators."""

import math

import numpy as np
import pytest

from anima.latex.glyph_body import GlyphBody, MeshQuality
from anima.latex.glyph_border import GlyphBorder
from anima.latex.triangulation import get_triangulator
from anima.utils.geometry import flatten_cubic_bezier, point_in_polygon
from tests.test_utils import create_rect_path, create_rect_with_hole_path

BACKENDS = ["earcut", "blender"]

# Cubic approximation of a quarter circle of unit radius.
K = 4.0 / 3.0 * math.tan(math.pi / 8.0)
QUARTER = ((1.0, 0.0), (1.0, K), (K, 1.0), (0.0, 1.0))


def _mesh_area(body: GlyphBody) -> float:
    verts = np.array([[v.x, v.y] for v in body._vertices])
    f = np.array(body._faces)
    a, b, c = verts[f[:, 0]], verts[f[:, 1]], verts[f[:, 2]]
    return float(0.5 * np.sum((b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0])))


class TestFlattenCubicBezier:
    def test_straight_curve_keeps_only_start(self):
        pts = flatten_cubic_bezier((0, 0), (1, 0), (2, 0), (3, 0), math.radians(5))
        assert pts == [(0.0, 0.0)]

    def test_includes_start_excludes_end(self):
        pts = flatten_cubic_bezier(*QUARTER, math.radians(10))
        assert pts[0] == (1.0, 0.0)
        assert (0.0, 1.0) not in pts

    @pytest.mark.parametrize("angle_deg", [5, 10, 30])
    def test_segment_turning_is_bounded(self, angle_deg):
        pts = np.array([*flatten_cubic_bezier(*QUARTER, math.radians(angle_deg)), QUARTER[3]])
        seg = np.diff(pts, axis=0)
        heading = np.arctan2(seg[:, 1], seg[:, 0])
        # Chord headings differ by at most the per-segment turning, plus a small interpolation slack.
        assert np.all(np.abs(np.diff(heading)) <= math.radians(angle_deg) * 1.15)

    def test_finer_angle_gives_more_points(self):
        coarse = flatten_cubic_bezier(*QUARTER, math.radians(30))
        fine = flatten_cubic_bezier(*QUARTER, math.radians(5))
        assert len(fine) > len(coarse) >= 3
        assert len(fine) == 18

    def test_points_lie_on_curve(self):
        pts = np.array(flatten_cubic_bezier(*QUARTER, math.radians(5)))
        assert np.allclose(np.hypot(pts[:, 0], pts[:, 1]), 1.0, atol=3e-4)

    def test_invalid_angle_raises(self):
        with pytest.raises(ValueError):
            flatten_cubic_bezier(*QUARTER, 0.0)


class TestPointInPolygon:
    def test_inside_and_outside(self):
        square = np.array([[0, 0], [2, 0], [2, 2], [0, 2]], dtype=float)
        assert point_in_polygon((1, 1), square)
        assert not point_in_polygon((3, 1), square)


@pytest.mark.parametrize("backend", BACKENDS)
class TestTriangulators:
    def test_square_with_hole(self, backend):
        outer = np.array([[0, 0], [10, 0], [10, 10], [0, 10]], dtype=float)
        hole = np.array([[3, 3], [3, 7], [7, 7], [7, 3]], dtype=float)
        faces = get_triangulator(backend).triangulate(outer, [hole])
        pts = np.concatenate([outer, hole])
        a, b, c = (pts[faces[:, i]] for i in range(3))
        areas = 0.5 * ((b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0]))
        assert np.all(areas > 0)
        assert areas.sum() == pytest.approx(100 - 16)
        assert faces.max() == len(pts) - 1

    def test_glyph_body_area(self, backend):
        quality = MeshQuality.minimal().evolve(triangulator=backend)
        solid = GlyphBody(GlyphBorder(create_rect_path()), mesh_quality=quality)
        assert _mesh_area(solid) == pytest.approx(100)
        holed = GlyphBody(GlyphBorder(create_rect_with_hole_path()), mesh_quality=quality)
        assert _mesh_area(holed) == pytest.approx(300)


def test_unknown_triangulator_raises():
    with pytest.raises(ValueError):
        get_triangulator("nope")
