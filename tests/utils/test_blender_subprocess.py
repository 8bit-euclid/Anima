"""Tests for Blender graphics GPU selection."""

import subprocess
from pathlib import Path

import pytest

from anima.utils import subprocess as blender_subprocess


@pytest.fixture
def linux(monkeypatch):
    monkeypatch.setattr(blender_subprocess.sys, "platform", "linux")


@pytest.mark.parametrize("existing", [{}, {"__NV_PRIME_RENDER_OFFLOAD": "1"}, {"__GLX_VENDOR_LIBRARY_NAME": "nvidia"}])
def test_defaults_to_nvidia_when_available(monkeypatch, linux, existing):
    monkeypatch.setattr(blender_subprocess.shutil, "which", lambda name: "/usr/bin/nvidia-smi")
    monkeypatch.setattr(
        blender_subprocess.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, stdout="0\n", stderr=""),
    )
    env = existing.copy()
    blender_subprocess._configure_viewport_gpu(env)
    assert env["__NV_PRIME_RENDER_OFFLOAD"] == "1"
    assert env["__GLX_VENDOR_LIBRARY_NAME"] == "nvidia"


def test_system_gpu_opt_out_is_respected(monkeypatch, linux):
    env = {"ANIMA_VIEWPORT_GPU": "system", "DRI_PRIME": "1"}
    original = env.copy()
    monkeypatch.setattr(blender_subprocess.shutil, "which", lambda name: pytest.fail("unexpected GPU probe"))
    blender_subprocess._configure_viewport_gpu(env)
    assert env == original


@pytest.mark.parametrize(
    "env", [{"DRI_PRIME": "1"}, {"__NV_PRIME_RENDER_OFFLOAD": "0"}, {"__GLX_VENDOR_LIBRARY_NAME": "mesa"}]
)
def test_conflicting_gpu_selection_is_rejected(monkeypatch, linux, env):
    monkeypatch.setattr(blender_subprocess.shutil, "which", lambda name: pytest.fail("unexpected GPU probe"))
    with pytest.raises(RuntimeError, match="conflict"):
        blender_subprocess._configure_viewport_gpu(env)


def test_unavailable_nvidia_stops_launch(monkeypatch, linux):
    monkeypatch.setattr(blender_subprocess.shutil, "which", lambda name: None)
    with pytest.raises(RuntimeError, match="nvidia-smi"):
        blender_subprocess._configure_viewport_gpu({})


@pytest.mark.parametrize("failure", ["nonzero", "empty", "timeout", "oserror"])
def test_failed_nvidia_probe_stops_launch(monkeypatch, linux, failure):
    monkeypatch.setattr(blender_subprocess.shutil, "which", lambda name: "/usr/bin/nvidia-smi")

    def probe(*args, **kwargs):
        if failure == "timeout":
            raise subprocess.TimeoutExpired(args[0], 5)
        if failure == "oserror":
            raise OSError("probe failed")
        return subprocess.CompletedProcess(args[0], int(failure == "nonzero"), stdout="", stderr="probe failed")

    monkeypatch.setattr(blender_subprocess.subprocess, "run", probe)
    with pytest.raises(RuntimeError, match="NVIDIA GPU"):
        blender_subprocess._configure_viewport_gpu({})


def test_invalid_viewport_gpu_is_rejected(linux):
    with pytest.raises(ValueError, match="ANIMA_VIEWPORT_GPU"):
        blender_subprocess._configure_viewport_gpu({"ANIMA_VIEWPORT_GPU": "unknown"})


@pytest.mark.parametrize("headless", [True, False])
def test_launch_configures_graphics_gpu(monkeypatch, headless):
    import anima.utils.blender as blender

    class Process:
        pid = 123

    captured = {}
    monkeypatch.setattr(blender, "get_blender_executable_path", lambda: Path("/test/blender"))
    monkeypatch.setattr(blender_subprocess, "get_script_path", lambda: Path("/test/lesson.py"))
    monkeypatch.setattr(blender_subprocess, "get_project_root_path", lambda: Path("/test"))

    def configure(env):
        env["__NV_PRIME_RENDER_OFFLOAD"] = "1"

    monkeypatch.setattr(blender_subprocess, "_configure_viewport_gpu", configure)

    def popen(command, **kwargs):
        captured.update(kwargs["env"])
        return Process()

    monkeypatch.setattr(blender_subprocess.subprocess, "Popen", popen)
    assert blender_subprocess.SubprocessManager(headless=headless).start()
    assert captured["PYTHONNOUSERSITE"] == "1"
    assert captured["__NV_PRIME_RENDER_OFFLOAD"] == "1"
