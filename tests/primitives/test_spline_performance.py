"""Regression tests for spline length caching and lazy arc-length lookup."""

import math
from copy import deepcopy

import numpy as np
import pytest
from scipy.integrate import quad

from anima.primitives import bezier_spline
from anima.primitives.bezier_curve import BezierCurve
from anima.primitives.bezier_spline import BezierSpline
from anima.primitives.chains import CurveChain
from anima.primitives.lines import Segment


def reference_length(curve, index, end):
    p0, p1, p2, p3 = (tuple(p) for p in curve._control_points(index))

    def speed(t):
        return math.sqrt(
            sum(
                (3 * ((1 - t) ** 2 * (p1[i] - p0[i]) + 2 * (1 - t) * t * (p2[i] - p1[i]) + t**2 * (p3[i] - p2[i]))) ** 2
                for i in range(3)
            )
        )

    return quad(speed, 0, end, epsabs=1e-10, epsrel=1e-10)[0]


@pytest.mark.parametrize(
    ("start", "end", "handles"),
    [
        ((0, 0), (4, 0), [(1, 0), (3, 0)]),
        ((0, 0), (4, 0), [(1, 2), (3, 2)]),
        ((0, 0), (0, 0), [(3, 5), (-3, 5)]),
        ((0, 0, 0), (1, 2, 3), [(3, -1, 4), (-2, 4, -1)]),
        ((0, 0), (0.00001, 0), [(0, 0.00002), (0.00001, 0.00002)]),
    ],
)
def test_arc_length_matches_reference(start, end, handles):
    curve = BezierCurve(start, end, control_pts=handles)
    for t in (0, 0.1, 0.5, 0.9, 1):
        assert curve.length(t) == pytest.approx(reference_length(curve, 0, t), rel=2e-6, abs=1e-8)


def test_lookup_is_lazy_and_reused_until_geometry_changes():
    curve = BezierCurve((0, 0), (4, 0), control_pts=[(0, 4), (3, 1)])
    assert curve._length_params is None
    curve.point(0)
    curve.point(1)
    assert curve._length_params is None

    curve.point(0.5)
    lookup = curve._length_params
    assert lookup is not None
    curve.set_param_1(0.3)
    curve.set_width(0.03)
    curve.set_bias(0.1)
    curve._update_length()
    assert curve._length_params is lookup

    previous_length = curve.length()
    curve.set_handle_0((0, 8), relative=False)
    assert curve._length_params is None
    assert curve.length() != pytest.approx(previous_length)
    curve.point(0.5)
    assert curve._length_params is not lookup


def test_handle_type_and_direct_edits_invalidate_lookup():
    curve = BezierCurve((0, 0), (4, 0), control_pts=[(0, 4), (3, 2)])
    curve.point(0.5)
    old_lookup = curve._length_params
    curve.set_right_handle_type(0, "VECTOR")
    assert curve._length_params is None
    curve.point(0.5)
    assert curve._length_params is not old_lookup

    old_length = curve._length
    curve.spline_point(1).co = (8, 0, 0)
    curve._update_length()
    assert curve._length_params is None
    assert curve._length != pytest.approx(old_length)
    assert curve._length == pytest.approx(reference_length(curve, 0, 1), rel=2e-6)


def test_arc_length_lookup_tracks_intermediate_parameters_after_edits():
    curve = BezierCurve((0, 0), (4, 0), control_pts=[(0, 4), (3, 1)])
    for handle in ((0, 4), (1, 7)):
        curve.set_handle_0(handle, relative=False)
        total = reference_length(curve, 0, 1)
        for fraction in (0.1, 0.25, 0.5, 0.75, 0.9):
            curve.set_param_1(fraction)
            parameter = curve.object.data.bevel_factor_end
            assert reference_length(curve, 0, parameter) == pytest.approx(total * fraction, abs=total * 0.001)


def test_chain_refreshes_child_after_external_geometry_edit():
    first = Segment((0, 0), (1, 0))
    second = Segment((1, 0), (2, 0))
    chain = CurveChain([first, second], create_joints=False)
    assert chain.length() == pytest.approx(2)
    second.spline_point(1).co = (3, 0, 0)
    chain.set_width(0.03)
    assert second._length == pytest.approx(reference_length(second, 0, 1), rel=2e-6)
    assert chain.length() == pytest.approx(first._length + second._length)


def test_multisegment_lookup_and_degenerate_curve():
    spline = BezierSpline([(0, 0), (1, 1), (3, 0)])
    assert spline._length_params is None
    spline.set_param_1(0.4)
    assert spline._length_params is not None
    assert np.all(np.diff(spline._length_params) >= 0)
    assert spline.object.data.bevel_factor_end == pytest.approx(spline._get_u_from_s(0.4 * spline._length))

    zero = Segment((0, 0), (0, 0))
    zero.point(0.5)
    assert zero._length == 0
    assert zero._length_params is not None


def test_deepcopy_has_independent_lookup_state():
    curve = BezierCurve((0, 0), (4, 0), control_pts=[(0, 4), (3, 2)])
    curve.point(0.5)
    copied = deepcopy(curve)
    copied.set_handle_0((0, 8), relative=False)
    assert copied._length_params is None
    assert curve._length_params is not None
    assert copied.length() != pytest.approx(curve.length())


def exact_cumulative_lengths(spline, params):
    """Return tightly integrated arc lengths at the given spline parameters."""
    num_segments = len(spline._spline_points()) - 1
    lengths = []
    for u in params:
        scaled = u * num_segments
        index = min(int(scaled), num_segments - 1)
        total = sum(reference_length(spline, i, 1) for i in range(index))
        lengths.append(total + reference_length(spline, index, scaled - index))
    return np.array(lengths)


LOOKUP_CURVES = {
    "generic": lambda: BezierCurve((0, 0), (4, 1), control_pts=[(1, 3), (3, -1)]),
    "cusp": lambda: BezierCurve((0, 0), (0, 0), control_pts=[(3, 5), (-3, 5)]),
    "straight": lambda: BezierCurve((0, 0), (4, 0), control_pts=[(1, 0), (3, 0)]),
    "overshoot": lambda: BezierCurve((0, 0), (4, 0), control_pts=[(5, 0), (-1, 0)]),
    "tiny": lambda: BezierCurve((0, 0), (1e-5, 0), control_pts=[(0, 2e-5), (1e-5, 2e-5)]),
    "multisegment": lambda: BezierSpline([(0, 0), (1, 1), (3, 0), (4, 2)]),
}


@pytest.mark.parametrize("name", LOOKUP_CURVES)
def test_lookup_lengths_match_reference_and_are_well_formed(name):
    spline = LOOKUP_CURVES[name]()
    spline.point(0.5)
    params, lengths = spline._spline_params, spline._length_params

    assert params[0] == 0 and params[-1] == 1
    assert np.all(np.diff(params) >= 0)
    assert np.all(np.diff(lengths) >= -1e-12)
    assert lengths[0] == pytest.approx(0, abs=1e-12)
    assert lengths[-1] == pytest.approx(spline.length(), rel=5e-4, abs=1e-8)

    num_segments = len(spline._spline_points()) - 1
    for i in range(1, num_segments):
        assert np.isclose(params, i / num_segments).any()

    scale = max(spline._length, 1e-9)
    error = np.max(np.abs(lengths - exact_cumulative_lengths(spline, params)))
    assert error <= 5e-4 * scale


def test_lookup_build_does_not_use_adaptive_integration(monkeypatch):
    spline = BezierSpline([(0, 0), (1, 1), (3, 0)])
    calls = []
    real_quad = bezier_spline.integrate.quad
    monkeypatch.setattr(bezier_spline.integrate, "quad", lambda *a, **k: calls.append(1) or real_quad(*a, **k))

    spline._map_u_to_s()
    assert calls == []


def test_each_geometry_edit_rebuilds_lookup_once(monkeypatch):
    curve = BezierCurve((0, 0), (4, 0), control_pts=[(0, 4), (3, 1)])
    builds = []
    real_build = BezierSpline._map_u_to_s
    monkeypatch.setattr(BezierSpline, "_map_u_to_s", lambda self: builds.append(1) or real_build(self))

    curve.point(0.5)
    assert len(builds) == 1
    for i in range(5):
        curve.point(0.3)
        curve.tangent(0.7)
        curve.set_handle_0((0, 4 + i + 1), relative=False)
        curve.point(0.5)
        curve.tangent(0.2)
    assert len(builds) == 6
