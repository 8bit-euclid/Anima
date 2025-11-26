def compute_signed_area(points: list[tuple[float, float]]) -> float:
    """Calculate the signed area of a polygon using the shoelace formula.

    Args:
        points: List of (x, y) tuples representing polygon vertices

    Returns:
        Signed area (positive for CCW, negative for CW winding)
    """
    return 0.5 * sum((x1 * y2 - x2 * y1) for (x1, y1), (x2, y2) in zip(points, points[1:] + [points[0]]))
