"""Apply an inward bump profile to a closed curve boundary."""

import math
from collections.abc import Callable

from anima.primitives.chains import CurveLoop
from anima.primitives.curve_profile import _disable_curve_shadows


def apply_emboss(boundary: CurveLoop, *, width: float, height: Callable[[float], float]) -> CurveLoop:
    """Apply an inward emboss profile to a closed boundary in place.

    The filled interior must be to the left of the curve. The height function
    runs from the boundary toward the interior. Its signed values affect bump
    shading, not geometry; the filled interior beyond the band is not displaced.

    Existing width, bias, and width profiles are replaced. Curve parts and
    endcaps stop casting shadows to avoid artifacts over the surface. Other
    objects sharing their materials also receive the new profile. Separate
    segments can leave gaps or overlap at corners.

    Args:
        boundary: Closed curve loop to modify.
        width: Inward band width in the boundary's local coordinate units.
        height: Function of normalized inward distance, from 0 at the boundary
            to 1 at the inner edge. Values are signed bump heights in scene units.

    Returns:
        The modified boundary.

    Raises:
        TypeError: If boundary is not a CurveLoop or height is not callable.
        ValueError: If width is not finite and positive, a sampled height is
            not finite, or a material cannot accommodate a width profile.
    """
    if not isinstance(boundary, CurveLoop):
        raise TypeError("boundary must be a CurveLoop.")
    if not math.isfinite(width) or width <= 0:
        raise ValueError("width must be finite and positive.")
    if not callable(height):
        raise TypeError("height must be callable.")

    boundary.set_width_profile(height=lambda u: height(1.0 - u))
    boundary.set_width(width)
    boundary.set_bias(-1)
    _disable_curve_shadows(boundary)
    return boundary
