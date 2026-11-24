"""Apply an outward opacity fade to a closed curve boundary."""

import math

from anima.primitives.chains import CurveLoop
from anima.primitives.curve_profile import set_width_profile
from anima.primitives.curves import Curve
from anima.primitives.endcaps import Endcap


def apply_bleed(boundary: CurveLoop, *, width: float, bias: float = 0.99) -> CurveLoop:
    """Apply an outward fade to a closed boundary in place.

    The filled interior must be to the left of the curve. Opacity is constant
    on the interior portion and fades linearly to zero on the exterior portion,
    multiplied by material opacity and texture coverage. The profile also
    affects other objects sharing the boundary's materials.

    Existing width, bias, and width profiles are replaced. Curve parts and
    endcaps stop casting shadows to avoid shadows between overlapping bands.
    Separate segments can leave gaps or overlap at corners.

    Args:
        boundary: Closed curve loop to modify.
        width: Outward fade distance in the boundary's local coordinate units.
        bias: Curve bias in (-1, 1]. Higher values reduce the inward overlap;
            1 places the entire width outside the boundary.

    Returns:
        The modified boundary.

    Raises:
        TypeError: If boundary is not a CurveLoop.
        ValueError: If bias is outside (-1, 1], width or the resulting total
            width is not finite and positive, or a material cannot accommodate
            a width profile.
    """
    if not isinstance(boundary, CurveLoop):
        raise TypeError("boundary must be a CurveLoop.")
    if isinstance(bias, bool) or not math.isfinite(bias) or not -1 < bias <= 1:
        raise ValueError("bias must be finite and in (-1, 1].")
    fraction = (1 + bias) / 2
    if not math.isfinite(width) or width <= 0 or not math.isfinite(width / fraction):
        raise ValueError("width and the resulting total width must be finite and positive.")

    set_width_profile(boundary, None, lambda u: 1.0 - u, 2, width_fraction=fraction)
    boundary.set_width(width / fraction)
    boundary.set_bias(bias)
    pending = [boundary]
    while pending:
        part = pending.pop()
        if isinstance(part, (Curve, Endcap)):
            part.object.visible_shadow = False
        pending.extend(part.children)
    return boundary
