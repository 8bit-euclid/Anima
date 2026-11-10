"""Profile-based render settings for scene entry points."""

from dataclasses import replace

from anima.scene.state import get_profile
from anima.utils.render import RenderSettings
from anima.utils.render_request import RenderRequest


def get_render_config() -> tuple[RenderSettings | None, RenderRequest | None]:
    """Read render options from the environment using the profile's resolutions.

    Returns:
        The render settings and request, or two None values when rendering is not requested.
    """
    request = RenderRequest.from_env()
    if request is None:
        return None, None
    profile = get_profile()
    settings = (
        RenderSettings(engine="EEVEE", samples=16, resolution=profile.preview_resolution)
        if request.preview
        else RenderSettings(engine="CYCLES", samples=256, resolution=profile.master_resolution, denoise=True)
    )
    return replace(settings, device=request.device), request
