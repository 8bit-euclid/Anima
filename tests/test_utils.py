"""Shared test utilities for Anima test suite."""

import pytest
import svgpathtools as svgtools

# =============================================================================
# SVG Path Helpers
# =============================================================================


def create_rect_path(x=0, y=0, width=10, height=10):
    """Create a simple rectangular SVG path.

    Args:
        x: X-coordinate of bottom-left corner.
        y: Y-coordinate of bottom-left corner.
        width: Width of the rectangle.
        height: Height of the rectangle.

    Returns:
        svgpathtools.Path: A closed rectangular path.
    """
    # Rectangle: bottom-left -> bottom-right -> top-right -> top-left -> close
    d = f"M {x},{y} L {x + width},{y} L {x + width},{y + height} L {x},{y + height} Z"
    return svgtools.parse_path(d)


def create_rect_with_hole_path():
    """Create a rectangular path with a hole inside.

    Returns:
        svgpathtools.Path: A rectangular path with an inner hole.
    """
    # Outer rectangle (CCW)
    outer = "M 0,0 L 20,0 L 20,20 L 0,20 Z"
    # Inner rectangle (CW) - the hole
    inner = "M 5,5 L 5,15 L 15,15 L 15,5 Z"
    return svgtools.parse_path(outer + " " + inner)


# =============================================================================
# General Assertions
# =============================================================================


def assert_vectors_equal(v1: list, v2: list, places: int = None):
    """Assert that two vectors are equal element-wise, up to a given decimal place.

    Args:
        v1: The first vector to compare (list, tuple, or Vector).
        v2: The second vector to compare (list, tuple, or Vector).
        places: The number of decimal places to check for equality.
            If None, checks for exact equality.

    Raises:
        AssertionError: If the vectors are not equal at any index.
    """
    for i in range(len(v1)):
        if places is not None:
            assert round(v1[i] - v2[i], places) == 0, f"{v1} != {v2} at index {i}"
        else:
            assert v1[i] == v2[i], f"{v1} != {v2} at index {i}"


def assert_death(func, *args, **kwargs):
    """Assert that calling func(*args, **kwargs) raises an AssertionError.

    Args:
        func: The function to call.
        *args: Positional arguments to pass to the function.
        **kwargs: Keyword arguments to pass to the function.

    Raises:
        AssertionError: If the function does not raise an AssertionError.
    """
    with pytest.raises(AssertionError):
        func(*args, **kwargs)


# =============================================================================
# Curve-Specific Assertions
# =============================================================================


def assert_curve_endpoints(curve, expected_start, expected_end, places: int = 6):
    """Assert that a curve starts and ends at the expected points.

    Args:
        curve: A Curve object with a point(t) method.
        expected_start: Expected position at t=0 (tuple, list, or Vector).
        expected_end: Expected position at t=1 (tuple, list, or Vector).
        places: Decimal places for floating-point comparison.

    Raises:
        AssertionError: If endpoints don't match expected values.
    """
    assert_vectors_equal(curve.point(0), expected_start, places=places)
    assert_vectors_equal(curve.point(1), expected_end, places=places)


def assert_curve_death_tests(curve):
    """Assert that all Curve methods raise AssertionError for out-of-bounds parameters.

    Tests point(), tangent(), normal(), and length() with parameters
    outside the valid [0, 1] range.

    Args:
        curve: A Curve object to test.

    Raises:
        AssertionError: If any method fails to raise for invalid parameters.
    """
    # Test point() bounds
    assert_death(curve.point, -0.1)
    assert_death(curve.point, 1.1)

    # Test tangent() bounds
    assert_death(curve.tangent, -0.1)
    assert_death(curve.tangent, 1.1)

    # Test normal() bounds
    assert_death(curve.normal, -0.1)
    assert_death(curve.normal, 1.1)

    # Test length() bounds
    assert_death(curve.length, -0.01)
    assert_death(curve.length, 1.01)


def assert_tangent_normal_perpendicular(curve, t: float, tol: float = 1e-6):
    """Assert that tangent and normal vectors are perpendicular at parameter t.

    This validates the mathematical invariant: tangent · normal = 0.

    Args:
        curve: A Curve object with tangent(t) and normal(t) methods.
        t: Parameter value in [0, 1] to test at.
        tol: Tolerance for the dot product (should be ~0).

    Raises:
        AssertionError: If tangent and normal are not perpendicular.
    """
    tangent = curve.tangent(t)
    normal = curve.normal(t)
    dot_product = tangent.dot(normal)
    assert abs(dot_product) < tol, f"tangent · normal = {dot_product} at t={t}, expected ~0 (tol={tol})"


def assert_setter_returns_self(obj, setter_name: str, value):
    """Assert that a setter method returns self for method chaining.

    Args:
        obj: The object containing the setter method.
        setter_name: Name of the setter method (e.g., 'set_width').
        value: Value to pass to the setter.

    Raises:
        AssertionError: If the setter does not return the same object.
    """
    setter = getattr(obj, setter_name)
    result = setter(value)
    assert result is obj, f"{setter_name}() should return self for chaining"


def assert_length_valid(curve, expected_total: float = None, places: int = 6):
    """Assert that length(0) = 0 and optionally that length(1) equals expected total.

    Args:
        curve: A Curve object with a length(u) method.
        expected_total: Expected total length at u=1. If None, only tests length(0).
        places: Decimal places for floating-point comparison.

    Raises:
        AssertionError: If length constraints are violated.
    """
    assert curve.length(0) == 0.0, "length(0) should be 0"
    if expected_total is not None:
        actual = curve.length(1)
        assert actual == pytest.approx(expected_total, rel=10 ** (-places)), (
            f"length(1) = {actual}, expected {expected_total}"
        )
