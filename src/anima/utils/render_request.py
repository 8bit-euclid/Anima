"""Environment-driven description of a requested render. Free of `bpy`, so it is usable outside Blender."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

_OFF = ("", "0", "false", "no")


def _flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() not in _OFF


@dataclass(frozen=True)
class RenderRequest:
    """What to render and where to put it.

    Attributes:
        video_path: The final MP4.
        frames_dir: Folder of PNG frames the video is encoded from. Frames survive crashes, so renders can resume.
        preview: Fast, lower-quality render for checking the animation.
        device: Cycles device, "GPU" or "CPU".
        bit_depth: PNG bit depth, 8 or 16.
        restart: Discard any frames already rendered instead of resuming.
        frame: If set, render only this frame to a still image and skip encoding.
    """

    video_path: Path
    frames_dir: Path
    preview: bool = False
    device: str = "GPU"
    bit_depth: int = 8
    restart: bool = False
    frame: int | None = None

    @property
    def still_path(self) -> Path:
        """Output image for a single-frame test render."""
        return self.video_path.with_name(f"{self.video_path.stem}_frame{self.frame}.png")

    @classmethod
    def from_env(cls) -> RenderRequest | None:
        """Build a request from the `ANIMA_RENDER*` environment variables.

        Returns:
            The request, or None when `ANIMA_RENDER` is unset (rendering not requested).
        """
        request = os.environ.get("ANIMA_RENDER", "").strip()
        if request.lower() in _OFF:
            return None

        preview = _flag("ANIMA_RENDER_PREVIEW")
        script = Path(os.environ.get("ANIMA_SCRIPT", "").strip() or "main")
        if request.lower() in ("1", "true", "yes"):
            video_path = Path(f"{script.stem}{'_preview' if preview else ''}.mp4")
        else:
            video_path = Path(request).expanduser()
        if video_path.parent == Path("."):
            video_path = Path("out") / video_path

        device = os.environ.get("ANIMA_RENDER_DEVICE", "").strip().upper() or "GPU"
        if device not in ("GPU", "CPU"):
            raise ValueError(f"ANIMA_RENDER_DEVICE must be GPU or CPU, got {device!r}")
        depth = os.environ.get("ANIMA_RENDER_DEPTH", "").strip() or "8"
        if depth not in ("8", "16"):
            raise ValueError(f"ANIMA_RENDER_DEPTH must be 8 or 16, got {depth!r}")
        frame = os.environ.get("ANIMA_RENDER_FRAME", "").strip()

        return cls(
            video_path=video_path,
            frames_dir=video_path.with_name(f"{video_path.stem}_frames"),
            preview=preview,
            device=device,
            bit_depth=int(depth),
            restart=_flag("ANIMA_RENDER_RESTART"),
            frame=int(frame) if frame else None,
        )
