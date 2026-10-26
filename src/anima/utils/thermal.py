"""NVIDIA GPU monitoring and thermal pausing for long renders (via `nvidia-smi`)."""

from __future__ import annotations

import shutil
import subprocess
import time
from typing import NamedTuple

from anima.diagnostics import logger


class GpuStatus(NamedTuple):
    """GPU temperature (°C) and memory (MiB)."""

    temperature: int
    memory_used: int
    memory_total: int


def gpu_status() -> GpuStatus | None:
    """Query the first NVIDIA GPU.

    Returns:
        The current status, or None if `nvidia-smi` is unavailable or fails.
    """
    if shutil.which("nvidia-smi") is None:
        return None
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=temperature.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"],
            text=True,
            timeout=10,
        )
        temp, used, total = (int(v) for v in out.splitlines()[0].split(","))
    except (subprocess.SubprocessError, ValueError, IndexError):
        return None
    return GpuStatus(temp, used, total)


def wait_until_cool(pause_at: int = 83, resume_at: int = 72, poll_seconds: float = 10.0) -> None:
    """Block while the GPU is too hot, so a laptop can cool between frames.

    Does nothing if the temperature is below `pause_at` or cannot be read. Once paused, waits until the
    temperature falls to `resume_at`.

    Args:
        pause_at: Temperature (°C) at or above which to pause.
        resume_at: Temperature (°C) at or below which to resume.
        poll_seconds: Time between temperature checks while paused.
    """
    status = gpu_status()
    if status is None or status.temperature < pause_at:
        return
    logger.warning(f"GPU at {status.temperature}°C (limit {pause_at}°C); pausing until it cools to {resume_at}°C")
    started = time.monotonic()
    while status is not None and status.temperature > resume_at:
        time.sleep(poll_seconds)
        status = gpu_status()
    logger.info(f"Resuming after {time.monotonic() - started:.0f}s pause")
