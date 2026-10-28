import math

import numpy as np


def compute_signed_area(points: list[tuple[float, float]]) -> float:
    """Calculate the signed area of a polygon using the shoelace formula.

    Args:
        points: List of (x, y) tuples representing polygon vertices

    Returns:
        Signed area (positive for CCW, negative for CW winding)
    """
    return 0.5 * sum((x1 * y2 - x2 * y1) for (x1, y1), (x2, y2) in zip(points, points[1:] + [points[0]]))


# Number of tangent samples used to measure a Bezier's turning. The tangent is evaluated away from t = 0 and 1,
# where it vanishes if a handle coincides with its anchor.
_TANGENT_SAMPLES = 48
_TANGENT_EPS = 1e-4


def flatten_cubic_bezier(
    p0: tuple[float, float],
    h0: tuple[float, float],
    h1: tuple[float, float],
    p1: tuple[float, float],
    max_turning_angle: float,
) -> list[tuple[float, float]]:
    """Flatten a cubic Bezier curve into a polyline with a bounded turning angle per segment.

    The total absolute turning of the tangent along the curve (inflections and cusps included) is divided into
    equal parts of at most `max_turning_angle`. Samples are therefore dense where the curve bends sharply and
    sparse where it is nearly straight; a straight curve yields only its start point.

    The result includes `p0` but excludes `p1`, so consecutive curves of a closed loop stitch without duplicates.

    Args:
        p0: Curve start point.
        h0: First control point.
        h1: Second control point.
        p1: Curve end point.
        max_turning_angle: Maximum tangent rotation, in radians, across any returned segment.

    Returns:
        The (x, y) sample points along the curve, starting with `p0`.
    """
    if max_turning_angle <= 0:
        raise ValueError("max_turning_angle must be positive")

    P = np.array([p0, h0, h1, p1], dtype=float)
    t = np.linspace(_TANGENT_EPS, 1.0 - _TANGENT_EPS, _TANGENT_SAMPLES)
    s = 1.0 - t
    d = 3.0 * (
        (s * s)[:, None] * (P[1] - P[0]) + (2.0 * s * t)[:, None] * (P[2] - P[1]) + (t * t)[:, None] * (P[3] - P[2])
    )

    cross = d[:-1, 0] * d[1:, 1] - d[:-1, 1] * d[1:, 0]
    dot = d[:-1, 0] * d[1:, 0] + d[:-1, 1] * d[1:, 1]
    turning = np.concatenate(([0.0], np.cumsum(np.abs(np.arctan2(cross, dot)))))
    total = turning[-1]

    num_segments = max(1, math.ceil(total / max_turning_angle - 1e-9))
    if num_segments == 1:
        return [p0]

    # Invert cumulative turning -> t to place samples at equal turning increments.
    ts = np.concatenate(([0.0], np.interp(np.arange(1, num_segments) * total / num_segments, turning, t)))
    s = 1.0 - ts
    pts = (
        (s**3)[:, None] * P[0]
        + (3.0 * s * s * ts)[:, None] * P[1]
        + (3.0 * s * ts * ts)[:, None] * P[2]
        + (ts**3)[:, None] * P[3]
    )
    pts[0] = P[0]
    return [(float(x), float(y)) for x, y in pts]


def point_in_polygon(point: np.ndarray | tuple[float, float], polygon: np.ndarray) -> bool:
    """Test whether a point lies inside a polygon using the even-odd ray casting rule.

    Args:
        point: The (x, y) point to test.
        polygon: (N, 2) polygon vertices.

    Returns:
        True if the point is inside the polygon.
    """
    x, y = point
    x0, y0 = polygon[:, 0], polygon[:, 1]
    x1, y1 = np.roll(x0, -1), np.roll(y0, -1)
    straddles = (y0 > y) != (y1 > y)
    with np.errstate(divide="ignore", invalid="ignore"):
        x_cross = x0 + (y - y0) * (x1 - x0) / (y1 - y0)
    return bool(np.count_nonzero(straddles & (x < x_cross)) % 2)
