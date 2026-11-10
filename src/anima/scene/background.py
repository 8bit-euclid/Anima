"""Create a textured background surface for a scene."""

import os
from pathlib import Path

from anima.materials.texture import TextureSet
from anima.primitives.polytopes import Rectangle
from anima.scene.state import get_background as get_background, get_profile, register_background

DEFAULT_BACKGROUND_TEXTURE_DIR = Path(os.environ.get("ANIMA_TEXTURE_DIR", "~/Downloads/Other_Paper_8K")).expanduser()


def create_background(
    texture_dir: str | Path,
    *,
    color: str = "#FEF3D7",
) -> Rectangle:
    """Create and register a textured rectangle behind the scene.

    Args:
        texture_dir: Directory containing recognized texture maps.
        color: Base color for the surface.

    Returns:
        The registered background rectangle.

    Raises:
        FileNotFoundError: If the directory is missing or contains no recognized texture maps.
    """
    profile = get_profile()
    textures = TextureSet.from_directory(texture_dir, physical_size=profile.texture_tile_size)
    if not textures.maps():
        raise FileNotFoundError(f"No background texture maps found in: {texture_dir}")
    background = Rectangle(*profile.background_size, name="Background")
    background.layer = -1
    background.set_color(color)
    background.set_textures(textures, bump_strength=profile.bump_strength, bump_distance=profile.bump_distance)
    register_background(background)
    return background
