"""Tests for profile-based rendering configuration."""

import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from anima.scene.profile import FRAME_16X9_V1
from anima.scene.render_config import get_render_config
from anima.scene.state import reset_profile, set_profile


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
