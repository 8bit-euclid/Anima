"""Tests for profile-based rendering configuration."""

import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from anima.scene.profile import FRAME_16X9_V1
from anima.scene.render_config import get_render_config
from anima.scene.state import reset_profile, set_profile
from anima.utils.render import RenderSettings
from anima.utils.render_request import RenderRequest


def test_render_config_is_opt_in(monkeypatch):
    monkeypatch.delenv("ANIMA_RENDER", raising=False)
    assert get_render_config() == (None, None)


@pytest.mark.parametrize(
    ("preview", "device", "engine", "samples", "resolution"),
    [
        ("0", "", "CYCLES", 256, (1280, 720)),
        ("1", "CPU", "EEVEE", 16, (640, 360)),
    ],
)
def test_render_config_uses_profile_and_request(monkeypatch, preview, device, engine, samples, resolution):
    monkeypatch.setenv("ANIMA_RENDER", "1")
    monkeypatch.setenv("ANIMA_RENDER_PREVIEW", preview)
    monkeypatch.setenv("ANIMA_RENDER_DEVICE", device)
    profile = replace(FRAME_16X9_V1, preview_resolution=(640, 360), master_resolution=(1280, 720))

    set_profile(profile)
    try:
        settings, request = get_render_config()
    finally:
        reset_profile()
    assert settings is not None
    assert request is not None
    assert (settings.engine, settings.samples, settings.resolution) == (engine, samples, resolution)
    assert settings.device == request.device == (device or "GPU")


def test_calibration_import_does_not_load_main():
    root = Path(__file__).resolve().parents[2]
    code = (
        "import runpy, sys; "
        f"sys.path.insert(0, {str(root / 'src')!r}); "
        f"runpy.run_path({str(root / 'scripts' / 'calibrate_dimensions.py')!r}); "
        "assert 'anima.main' not in sys.modules; "
        "assert not any(name.startswith('tests.visual_tests') for name in sys.modules)"
    )
    subprocess.run([sys.executable, "-c", code], cwd=root, env=os.environ.copy(), check=True)


@pytest.mark.parametrize("device", [None, "CPU"])
def test_cycles_render_defaults_to_nvidia_gpu_but_allows_cpu(monkeypatch, device):
    import anima.utils.render as render

    scene = SimpleNamespace(render=SimpleNamespace(), cycles=SimpleNamespace())
    enable_gpu = MagicMock(return_value=["NVIDIA GPU"])
    monkeypatch.setattr(render, "bpy", SimpleNamespace(context=SimpleNamespace(scene=scene)))
    monkeypatch.setattr(render, "enable_gpu_devices", enable_gpu)
    settings = RenderSettings() if device is None else RenderSettings(device=device)

    render.configure_render(settings)

    assert scene.cycles.device == (device or "GPU")
    assert enable_gpu.call_count == (0 if device == "CPU" else 1)


@pytest.mark.parametrize("device", ["GPU", "CPU"])
def test_render_request_without_settings_configures_requested_device(monkeypatch, device):
    import anima.runtime as runtime

    monkeypatch.setattr(runtime, "bpy", SimpleNamespace(app=SimpleNamespace(background=True, driver_namespace={})))
    monkeypatch.setattr(runtime, "clear_scene", lambda: None)
    monkeypatch.setattr(runtime, "hide_relationship_lines", lambda: None)
    monkeypatch.setattr(runtime, "deselect_all", lambda: None)
    monkeypatch.setattr(runtime, "Scheduler", MagicMock())
    monkeypatch.setattr(runtime, "ebpy", MagicMock())
    configure = MagicMock()
    render = MagicMock()
    monkeypatch.setattr(runtime, "configure_render", configure)
    monkeypatch.setattr(runtime, "_render", render)
    request = RenderRequest(video_path=Path("test.mp4"), frames_dir=Path("test_frames"), device=device)

    runtime.run_lesson(lambda _start, _end: None, end_time="00:02", use_default_lighting=False, render_request=request)

    settings = configure.call_args.args[0]
    assert settings.device == device
    render.assert_called_once_with(request, settings)
