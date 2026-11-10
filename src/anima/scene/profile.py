"""Versioned dimensions for the default mathematical video frame."""

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class VisualProfile:
    """Dimensions and visual defaults for a landscape video series.

    Lengths are in scene units unless otherwise specified. Typography sizes
    are in TeX points; ``tex_point_size`` converts a TeX point to scene units.
    """

    name: str = "paper-16x9-v1"
    frame_width: float = 20.0
    aspect_width: int = 16
    aspect_height: int = 9
    safe_margin: float = 0.05
    background_bleed: float = 0.2
    texture_tile_size: float = 10.0
    bump_strength: float = 0.5
    bump_distance: float = 0.1
    tex_point_size: float = 0.05
    body_font_size: float = 10.0
    label_font_size: float = 7.5
    title_font_size: float = 15.0
    preview_resolution: tuple[int, int] = (1920, 1080)
    master_resolution: tuple[int, int] = (3840, 2160)
    frame_rate: int = 60
    camera_height: float = 10.0
    clip_start: float = 0.1
    clip_end: float = 100.0
    sun_rotation: tuple[float, float, float] = (0.9, 0.3, 0.5)
    sun_energy: float = 4.0

    def __post_init__(self) -> None:
        positive = (
            self.frame_width,
            self.texture_tile_size,
            self.tex_point_size,
            self.body_font_size,
            self.label_font_size,
            self.title_font_size,
            self.camera_height,
            self.clip_start,
            self.clip_end,
            self.sun_energy,
        )
        if not all(isfinite(value) and value > 0 for value in positive):
            raise ValueError("Frame, typography, texture, camera and clipping dimensions must be finite and positive.")
        if not all(
            isinstance(value, int) and not isinstance(value, bool) and value > 0
            for value in (self.aspect_width, self.aspect_height, self.frame_rate)
        ):
            raise ValueError("Aspect ratio and frame rate must be positive.")
        if not all(isfinite(value) for value in self.sun_rotation):
            raise ValueError("Sun rotation must be finite.")
        if not isfinite(self.safe_margin) or not 0 <= self.safe_margin < 0.5:
            raise ValueError("Safe margin must be finite and in [0, 0.5).")
        if not isfinite(self.background_bleed) or self.background_bleed < 0:
            raise ValueError("Background bleed must be finite and nonnegative.")
        if not isfinite(self.bump_strength) or not 0 <= self.bump_strength <= 1:
            raise ValueError("Bump strength must be finite and in [0, 1].")
        if not isfinite(self.bump_distance) or self.bump_distance < 0:
            raise ValueError("Bump distance must be finite and nonnegative.")
        if not self.clip_start < self.camera_height < self.clip_end:
            raise ValueError("The background plane must be between the camera clipping planes.")
        for resolution in (self.preview_resolution, self.master_resolution):
            self.validate_resolution(resolution)

    @property
    def frame_height(self) -> float:
        """Visible height at the default framing, in scene units."""
        return self.frame_width * self.aspect_height / self.aspect_width

    @property
    def background_size(self) -> tuple[float, float]:
        """Background width and height including bleed on all sides."""
        return self.frame_width + 2 * self.background_bleed, self.frame_height + 2 * self.background_bleed

    @property
    def safe_size(self) -> tuple[float, float]:
        """Width and height of the centered layout-safe area."""
        factor = 1 - 2 * self.safe_margin
        return self.frame_width * factor, self.frame_height * factor

    def validate_resolution(self, resolution: tuple[int, int]) -> None:
        """Require a positive integer resolution matching the profile aspect ratio.

        Raises:
            ValueError: If the resolution is invalid or has a different aspect ratio.
        """
        width, height = resolution
        if (
            not all(isinstance(value, int) and not isinstance(value, bool) and value > 0 for value in resolution)
            or width * self.aspect_height != height * self.aspect_width
        ):
            raise ValueError(
                f"Resolution {resolution} does not match the {self.aspect_width}:{self.aspect_height} profile."
            )

    def pixels_per_unit(self, resolution: tuple[int, int]) -> float:
        """Return the pixels per scene unit at the default camera framing."""
        self.validate_resolution(resolution)
        return resolution[0] / self.frame_width


FRAME_16X9_V1 = VisualProfile()
