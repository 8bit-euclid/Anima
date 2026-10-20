"""Render-engine configuration and still/animation rendering."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import bpy

Engine = Literal["CYCLES", "EEVEE"]

_ENGINE_IDS = {"CYCLES": "CYCLES", "EEVEE": "BLENDER_EEVEE"}


@dataclass
class RenderSettings:
    """Render configuration shared by both engines.

    Attributes:
        engine: "CYCLES" (path tracer; most physically accurate) or "EEVEE" (real-time; much faster).
        samples: Samples per pixel.
        resolution: Output (width, height) in pixels.
        device: Cycles device: "CPU" or "GPU". Ignored by EEVEE.
        denoise: Denoise the Cycles result.
    """

    engine: Engine = "CYCLES"
    samples: int = 64
    resolution: tuple[int, int] = (1920, 1080)
    device: Literal["CPU", "GPU"] = "CPU"
    denoise: bool = True


def configure_render(settings: RenderSettings | None = None) -> RenderSettings:
    """Apply render settings to the current scene.

    Args:
        settings: The settings to apply. Defaults to `RenderSettings()`.

    Returns:
        The settings that were applied.
    """
    settings = settings or RenderSettings()
    scene = bpy.context.scene
    scene.render.engine = _ENGINE_IDS[settings.engine]
    scene.render.resolution_x, scene.render.resolution_y = settings.resolution
    scene.render.resolution_percentage = 100
    if settings.engine == "CYCLES":
        scene.cycles.samples = settings.samples
        scene.cycles.device = settings.device
        scene.cycles.use_denoising = settings.denoise
    else:
        scene.eevee.taa_render_samples = settings.samples
    return settings


def ensure_camera(location: tuple[float, float, float] = (0, 0, 10), orthographic_scale: float | None = None):
    """Make sure the scene has an active camera, creating a top-down one if needed.

    Args:
        location: Camera location for a newly created camera (it looks straight down -Z).
        orthographic_scale: If given, a new camera is orthographic with this scale.

    Returns:
        The scene's active camera object.
    """
    scene = bpy.context.scene
    if scene.camera is not None:
        return scene.camera
    data = bpy.data.cameras.new("Camera")
    if orthographic_scale is not None:
        data.type = "ORTHO"
        data.ortho_scale = orthographic_scale
    camera = bpy.data.objects.new("Camera", data)
    scene.collection.objects.link(camera)
    camera.location = location
    scene.camera = camera
    return camera


def render_still(path: str | Path) -> Path:
    """Render the current frame to an image file.

    Args:
        path: Output file path (the extension selects nothing; the format is the scene's, PNG by default).

    Returns:
        The output path.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return path


def render_animation(path: str | Path, ffmpeg: bool = True) -> Path:
    """Render the scene's frame range.

    Args:
        path: Output movie file (when `ffmpeg` is True) or a frame-filename prefix (otherwise).
        ffmpeg: Encode an H.264 MP4 instead of writing an image sequence.

    Returns:
        The output path.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    render = bpy.context.scene.render
    if ffmpeg:
        render.image_settings.file_format = "FFMPEG"
        render.ffmpeg.format = "MPEG4"
        render.ffmpeg.codec = "H264"
        render.ffmpeg.constant_rate_factor = "HIGH"
    render.filepath = str(path)
    bpy.ops.render.render(animation=True)
    return path
