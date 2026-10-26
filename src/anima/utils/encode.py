"""Encode a rendered PNG frame sequence into a YouTube-ready MP4 with ffmpeg. Free of `bpy`."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

from anima.diagnostics import logger

MANIFEST_NAME = "manifest.json"
FRAME_PATTERN = "frame_{:04d}.png"
_PNG_TRAILER = b"\x00\x00\x00\x00IEND\xaeB`\x82"


def is_valid_frame(path: Path) -> bool:
    """Whether `path` is a complete PNG (non-empty and ending with the IEND chunk)."""
    try:
        size = path.stat().st_size
        if size < len(_PNG_TRAILER):
            return False
        with path.open("rb") as f:
            f.seek(-len(_PNG_TRAILER), 2)
            return f.read() == _PNG_TRAILER
    except OSError:
        return False


_PROGRESS_KEYS = {
    "frame", "fps", "bitrate", "total_size", "out_time_us", "out_time_ms", "out_time", "dup_frames", "drop_frames",
    "speed", "progress",
}  # fmt: skip


def _run_logged(command: list[str], log_every: float = 5.0) -> int:
    """Run ffmpeg, sending its progress and diagnostics through the logger.

    Args:
        command: The ffmpeg command, which must use `-progress pipe:1`.
        log_every: Minimum seconds between progress messages.

    Returns:
        The process exit code.
    """
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    last_log = 0.0
    fields: dict[str, str] = {}
    for line in process.stdout:
        line = line.strip()
        if not line:
            continue
        key, _, value = line.partition("=")
        if key not in _PROGRESS_KEYS and not key.startswith("stream_"):
            logger.warning(f"[ffmpeg] {line}")
            continue
        fields[key] = value
        if key == "progress" and (value == "end" or time.monotonic() - last_log >= log_every):
            last_log = time.monotonic()
            logger.info(f"[ffmpeg] frame {fields.get('frame')}, {fields.get('fps')} fps, speed {fields.get('speed')}")
    return process.wait()


def encode_video(frames_dir: str | Path, video_path: str | Path, crf: int | None = None, preset: str = "slow") -> Path:
    """Encode the frames in `frames_dir` to H.264 MP4.

    The frame range and frame rate come from the manifest written by the renderer. The output is 8-bit
    4:2:0 BT.709, which YouTube accepts and re-encodes.

    Args:
        frames_dir: Folder containing `frame_NNNN.png` files and the manifest.
        video_path: Output MP4 path.
        crf: x264 constant rate factor (lower is better). Defaults to 16, or 23 for preview renders.
        preset: x264 preset; slower presets give smaller files at the same quality.

    Returns:
        The output path.

    Raises:
        RuntimeError: If ffmpeg is missing, frames are missing or corrupt, or encoding fails.
    """
    frames_dir, video_path = Path(frames_dir), Path(video_path)
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not found. Install it with: sudo apt install ffmpeg")
    manifest = json.loads((frames_dir / MANIFEST_NAME).read_text())
    start, end, fps = manifest["frame_start"], manifest["frame_end"], manifest["fps"]
    if crf is None:
        crf = 23 if manifest.get("preview") else 16

    bad = [f for f in range(start, end + 1) if not is_valid_frame(frames_dir / FRAME_PATTERN.format(f))]
    if bad:
        raise RuntimeError(
            f"{len(bad)} of {end - start + 1} frames are missing or corrupt (first: {bad[0]}). Re-run the render to resume."
        )

    video_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning", "-nostats", "-progress", "pipe:1",
        "-framerate", str(fps),
        "-start_number", str(start),
        "-i", str(frames_dir / "frame_%04d.png"),
        "-frames:v", str(end - start + 1),
        "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
        "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
        "-movflags", "+faststart",
        str(video_path),
    ]  # fmt: skip
    logger.info(f"Encoding {end - start + 1} frames at {fps} fps to {video_path} (crf {crf}, preset {preset})")
    if _run_logged(command) != 0:
        raise RuntimeError("ffmpeg failed")
    logger.info(f"Video written: {video_path}")
    return video_path


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point: `python -m anima.utils.encode FRAMES_DIR VIDEO [--crf N] [--preset P]`."""
    parser = argparse.ArgumentParser(description="Encode a rendered frame sequence to MP4.")
    parser.add_argument("frames_dir")
    parser.add_argument("video_path")
    parser.add_argument("--crf", type=int)
    parser.add_argument("--preset", default="slow")
    args = parser.parse_args(argv)
    try:
        encode_video(args.frames_dir, args.video_path, args.crf, args.preset)
    except (RuntimeError, OSError, KeyError) as e:
        logger.error(f"Encoding failed: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
