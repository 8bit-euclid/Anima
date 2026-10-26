"""Render-engine configuration and still/animation rendering."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import bpy

from anima.diagnostics import logger
from anima.utils.encode import FRAME_PATTERN, MANIFEST_NAME, is_valid_frame
from anima.utils.thermal import gpu_status, wait_until_cool

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
        denoiser: "OPTIX" (fast, needs an NVIDIA RTX GPU) or "OPENIMAGEDENOISE" (slower, works anywhere).
        tile_size: Cycles tile edge in pixels. Tiling only bounds render/denoise buffers, not scene memory.
    """

    engine: Engine = "CYCLES"
    samples: int = 64
    resolution: tuple[int, int] = (1920, 1080)
    device: Literal["CPU", "GPU"] = "CPU"
    denoise: bool = True
    denoiser: Literal["OPTIX", "OPENIMAGEDENOISE"] = "OPTIX"
    tile_size: int = 1024


def enable_gpu_devices() -> list[str]:
    """Enable only the GPU devices for Cycles (OptiX preferred, then CUDA); the CPU is disabled.

    Returns:
        The names of the enabled devices.

    Raises:
        RuntimeError: If no OptiX or CUDA GPU is found.
    """
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for backend in ("OPTIX", "CUDA"):
        prefs.compute_device_type = backend
        prefs.refresh_devices()
        gpus = [d for d in prefs.devices if d.type == backend]
        if gpus:
            for device in prefs.devices:
                device.use = device.type == backend
            return [d.name for d in gpus]
    raise RuntimeError("No OptiX/CUDA GPU found for Cycles. Check the NVIDIA driver, or render on the CPU.")


def configure_render(settings: RenderSettings | None = None) -> RenderSettings:
    """Apply render settings to the current scene.

    Args:
        settings: The settings to apply. Defaults to `RenderSettings()`.

    Returns:
        The settings that were applied.

    Raises:
        RuntimeError: If a GPU is requested for Cycles but none is available.
    """
    settings = settings or RenderSettings()
    scene = bpy.context.scene
    scene.render.engine = _ENGINE_IDS[settings.engine]
    scene.render.resolution_x, scene.render.resolution_y = settings.resolution
    scene.render.resolution_percentage = 100
    if settings.engine == "CYCLES":
        scene.cycles.samples = settings.samples
        scene.cycles.use_adaptive_sampling = True
        scene.cycles.use_denoising = settings.denoise
        scene.cycles.denoiser = settings.denoiser
        scene.cycles.use_auto_tile = True
        scene.cycles.tile_size = settings.tile_size
        scene.render.use_persistent_data = False
        scene.cycles.device = settings.device
        if settings.device == "GPU":
            logger.info(f"Cycles GPU devices: {', '.join(enable_gpu_devices())}")
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


def render_animation(path: str | Path, ffmpeg: bool = True, quality: str = "HIGH") -> Path:
    """Render the scene's frame range.

    Args:
        path: Output movie file (when `ffmpeg` is True) or a frame-filename prefix (otherwise).
        ffmpeg: Encode an H.264 MP4 instead of writing an image sequence.
        quality: Blender's FFmpeg constant rate factor (e.g. "MEDIUM", "HIGH", "PERC_LOSSLESS"). Ignored
            unless `ffmpeg` is True.

    Returns:
        The output path.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    render = bpy.context.scene.render
    if ffmpeg:
        render.image_settings.file_format = "FFMPEG"
        render.image_settings.color_mode = "RGB"
        render.ffmpeg.format = "MPEG4"
        render.ffmpeg.codec = "H264"
        render.ffmpeg.constant_rate_factor = quality
        render.ffmpeg.ffmpeg_preset = "GOOD"
        render.ffmpeg.audio_codec = "NONE"
    render.filepath = str(path)
    bpy.ops.render.render(animation=True)
    return path


def _configure_png(bit_depth: int) -> None:
    """Set the scene to write RGB PNG frames at the given bit depth."""
    image = bpy.context.scene.render.image_settings
    image.file_format = "PNG"
    image.color_mode = "RGB"
    image.color_depth = str(bit_depth)
    image.compression = 15


def render_frame(path: str | Path, frame: int, bit_depth: int = 8) -> Path:
    """Render a single frame to a PNG, leaving the scene's current frame unchanged.

    Args:
        path: Output PNG path.
        frame: The frame to render.
        bit_depth: PNG bit depth, 8 or 16.

    Returns:
        The output path.
    """
    scene = bpy.context.scene
    original_frame = scene.frame_current
    _configure_png(bit_depth)
    scene.frame_set(frame)
    try:
        render_still(path)
    finally:
        scene.frame_set(original_frame)
    return Path(path)


def _prepare_frames_dir(frames_dir: Path, manifest: dict, restart: bool) -> None:
    """Create `frames_dir`, discard stale frames on restart, and guard against resuming a different render.

    Raises:
        RuntimeError: If frames from a render with different settings exist and `restart` is False.
    """
    frames_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = frames_dir / MANIFEST_NAME
    if restart:
        for stale in frames_dir.glob("frame_*.png"):
            stale.unlink()
        manifest_path.unlink(missing_ok=True)
    elif manifest_path.exists() and json.loads(manifest_path.read_text()) != manifest:
        raise RuntimeError(
            f"{frames_dir} holds frames rendered with different settings. Set ANIMA_RENDER_RESTART=1 to discard "
            "them, or choose a different output path."
        )
    manifest_path.write_text(json.dumps(manifest, indent=2))


def render_sequence(
    frames_dir: str | Path,
    settings: RenderSettings,
    bit_depth: int = 8,
    restart: bool = False,
    preview: bool = False,
    pause_at_c: int = 83,
    resume_at_c: int = 72,
) -> Path:
    """Render the scene's frame range to PNG files, resumably, pausing whenever the GPU is too hot.

    Frames that already exist and are complete are skipped, so an interrupted render continues where it left
    off. This assumes the scene itself has not changed since those frames were rendered; use `restart` after
    editing it. Progress, per-frame time, ETA, GPU temperature and VRAM are logged.

    Args:
        frames_dir: Output folder; frames are named `frame_NNNN.png`.
        settings: The settings the scene was configured with (recorded so incompatible resumes are refused).
        bit_depth: PNG bit depth, 8 or 16.
        restart: Delete existing frames and start over.
        preview: Recorded in the manifest so the encoder picks preview quality.
        pause_at_c: GPU temperature (°C) at which to pause between frames.
        resume_at_c: GPU temperature (°C) at which to resume.

    Returns:
        The frames folder.

    Raises:
        RuntimeError: If existing frames were rendered with different settings and `restart` is False.
    """
    frames_dir = Path(frames_dir)
    scene = bpy.context.scene
    first, last = scene.frame_start, scene.frame_end
    manifest = {
        "engine": settings.engine,
        "samples": settings.samples,
        "resolution": list(settings.resolution),
        "denoiser": settings.denoiser if settings.denoise else None,
        "device": settings.device,
        "bit_depth": bit_depth,
        "fps": scene.render.fps,
        "frame_start": first,
        "frame_end": last,
        "preview": preview,
    }
    _prepare_frames_dir(frames_dir, manifest, restart)
    _configure_png(bit_depth)

    total = last - first + 1
    pending = [f for f in range(first, last + 1) if not is_valid_frame(frames_dir / FRAME_PATTERN.format(f))]
    logger.info(f"Rendering frames {first}-{last} to {frames_dir}: {total - len(pending)} done, {len(pending)} to go")

    durations: list[float] = []
    try:
        for index, frame in enumerate(pending, start=1):
            wait_until_cool(pause_at_c, resume_at_c)
            started = time.monotonic()
            scene.frame_set(frame)
            render_still(frames_dir / FRAME_PATTERN.format(frame))
            durations.append(time.monotonic() - started)

            recent = durations[-10:]
            eta_minutes = sum(recent) / len(recent) * (len(pending) - index) / 60
            status = gpu_status()
            gpu = f", GPU {status.temperature}°C, VRAM {status.memory_used}/{status.memory_total} MiB" if status else ""
            logger.info(
                f"Frame {frame} ({index}/{len(pending)}) in {durations[-1]:.1f}s, ETA {eta_minutes:.0f} min{gpu}"
            )
    except KeyboardInterrupt:
        logger.warning("Render interrupted; re-run to resume from the next unfinished frame")
        raise

    logger.info(f"Render complete: {total} frames in {frames_dir}")
    return frames_dir
