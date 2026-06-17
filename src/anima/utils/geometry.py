def compute_signed_area(points: list[tuple[float, float]]) -> float:
    """Calculate the signed area of a polygon using the shoelace formula.

    Args:
        points: List of (x, y) tuples representing polygon vertices

    Returns:
        Signed area (positive for CCW, negative for CW winding)
    """
    return 0.5 * sum((x1 * y2 - x2 * y1) for (x1, y1), (x2, y2) in zip(points, points[1:] + [points[0]]))


def flatten_cubic_bezier(
    p0: tuple[float, float],
    h0: tuple[float, float],
    h1: tuple[float, float],
    p1: tuple[float, float],
    tolerance: float,
    max_depth: int = 18,
) -> tuple[list[tuple[float, float]], list[float]]:
    """Adaptively flatten a cubic Bezier curve into a polyline.

    Uses recursive de Casteljau subdivision driven by a control-polygon
    flatness test: a curve is "flat enough" when both control handles lie
    within `tolerance` of the chord joining its endpoints. The result is
    naturally curvature-adaptive: dense samples appear in high-curvature
    regions, sparse samples on near-straight stretches.

    The returned points list INCLUDES the start point `p0` (and any
    subdivision points generated) but EXCLUDES the end point `p1`. This
    keeps the stitching across consecutive curves duplicate-free: the
    caller appends the next curve's start (or wraps back to the first) as
    the closing vertex. The parallel `params` list contains the curve
    parameter t in [0, 1) of each returned point (with `params[0] == 0.0`).

    Args:
        p0: Curve start point (x, y).
        h0: First control handle (x, y).
        h1: Second control handle (x, y).
        p1: Curve end point (x, y).
        tolerance: Maximum permitted perpendicular distance from a control
            handle to the chord p0-p1, in the same units as the points.
            Smaller values yield denser sampling.
        max_depth: Hard recursion depth cap (safety). With `tolerance > 0`
            this is essentially never hit in practice.

    Returns:
        A 2-tuple `(points, params)` where `points` is a list of (x, y)
        tuples along the curve and `params` is the matching list of
        curve parameters t in [0, 1).
    """
    tolerance_sq = tolerance * tolerance

    def _recurse(
        a: tuple[float, float],
        b: tuple[float, float],
        c: tuple[float, float],
        d: tuple[float, float],
        t0: float,
        t1: float,
        depth: int,
    ) -> tuple[list[tuple[float, float]], list[float]]:
        cx, cy = d[0] - a[0], d[1] - a[1]
        chord_len_sq = cx * cx + cy * cy

        if chord_len_sq == 0.0:
            # Degenerate chord (start == end). Fall back to handle spread
            # so that loops still get subdivided.
            spread_sq = max(
                (b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2,
                (c[0] - d[0]) ** 2 + (c[1] - d[1]) ** 2,
            )
            is_flat = spread_sq <= tolerance_sq
        else:
            # Perpendicular distance (squared) from a handle to the chord.
            vbx, vby = b[0] - a[0], b[1] - a[1]
            vcx, vcy = c[0] - a[0], c[1] - a[1]
            cross_b = vbx * cy - vby * cx
            cross_c = vcx * cy - vcy * cx
            max_perp_sq = max(cross_b * cross_b, cross_c * cross_c) / chord_len_sq
            is_flat = max_perp_sq <= tolerance_sq

        if is_flat or depth >= max_depth:
            return [a], [t0]

        # de Casteljau subdivision at t = 0.5
        ab = ((a[0] + b[0]) * 0.5, (a[1] + b[1]) * 0.5)
        bc = ((b[0] + c[0]) * 0.5, (b[1] + c[1]) * 0.5)
        cd = ((c[0] + d[0]) * 0.5, (c[1] + d[1]) * 0.5)
        abc = ((ab[0] + bc[0]) * 0.5, (ab[1] + bc[1]) * 0.5)
        bcd = ((bc[0] + cd[0]) * 0.5, (bc[1] + cd[1]) * 0.5)
        mid = ((abc[0] + bcd[0]) * 0.5, (abc[1] + bcd[1]) * 0.5)
        tm = (t0 + t1) * 0.5

        left_pts, left_ts = _recurse(a, ab, abc, mid, t0, tm, depth + 1)
        right_pts, right_ts = _recurse(mid, bcd, cd, d, tm, t1, depth + 1)
        return left_pts + right_pts, left_ts + right_ts

    return _recurse(p0, h0, h1, p1, 0.0, 1.0, 0)
