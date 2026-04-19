"""Utility functions for converting SVG paths to Anima curves.

This module provides functions to convert svgpathtools segments and paths
into Anima curve primitives (Segment, BezierCurve, etc.).
"""

import svgpathtools as svgtools

from anima.primitives.bezier_curve import BezierCurve
from anima.primitives.curves import Curve
from anima.primitives.lines import Segment


def svg_segment_to_curve(
    seg,
    reflect_y: bool = True,
    reverse_direction: bool = False,
) -> Curve:
    """Convert a single SVG segment to an Anima Curve.

    Args:
        seg: An svgpathtools segment (Line or CubicBezier).
        reflect_y: If True, negate y-coordinates to convert from SVG's
            y-down to Blender's y-up coordinate system.
        reverse_direction: If True, swap start and end points to reverse
            the curve direction.

    Returns:
        An Anima Curve (Segment or BezierCurve).

    Raises:
        ValueError: If the segment type is not supported.
    """
    # Determine start and end points based on direction
    if reverse_direction:
        start = seg.end
        end = seg.start
    else:
        start = seg.start
        end = seg.end

    # Apply y-reflection if needed
    y_mult = -1 if reflect_y else 1
    p0 = (start.real, y_mult * start.imag)
    p1 = (end.real, y_mult * end.imag)

    if isinstance(seg, svgtools.Line):
        return Segment(p0, p1)

    elif isinstance(seg, svgtools.CubicBezier):
        # Control points also need to be swapped if reversing direction
        if reverse_direction:
            ctrl1 = seg.control2
            ctrl2 = seg.control1
        else:
            ctrl1 = seg.control1
            ctrl2 = seg.control2

        c0 = (ctrl1.real, y_mult * ctrl1.imag)
        c1 = (ctrl2.real, y_mult * ctrl2.imag)
        return BezierCurve(p0, p1, control_pts=[c0, c1])

    else:
        raise ValueError(f"Unsupported SVG segment type: {type(seg)}")


def svg_path_to_curves(
    path,
    reflect_y: bool = True,
    reverse: bool = True,
) -> list[Curve]:
    """Convert an SVG path to a list of Anima Curves.

    Args:
        path: An svgpathtools.Path object.
        reflect_y: If True, negate y-coordinates to convert from SVG's
            y-down to Blender's y-up coordinate system.
        reverse: If True, reverse both the order of segments and the
            direction of each segment. This is typically needed for
            correct winding order in triangulation.

    Returns:
        A list of Anima Curve objects.
    """
    curves = []

    # Determine iteration order
    segments = reversed(path) if reverse else path

    for seg in segments:
        curve = svg_segment_to_curve(
            seg,
            reflect_y=reflect_y,
            reverse_direction=reverse,
        )
        curves.append(curve)

    return curves
