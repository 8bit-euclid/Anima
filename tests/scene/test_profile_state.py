"""Tests for scene-scoped visual profile configuration."""

import importlib
import subprocess
import sys
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import MagicMock

import bpy
import pytest

import anima.globals.general as general
from anima.scene.profile import FRAME_16X9_V1
from anima.scene.setup import configure_camera, configure_lighting
from anima.scene.state import get_profile, reset_profile, set_profile


def test_profile_is_scoped_to_scene_and_survives_reload_and_clear(monkeypatch):
    import anima.scene.state as state

    window = bpy.context.window
    original_scene = window.scene
    scene_a = bpy.data.scenes.new("pytest_profile_a")
    scene_b = bpy.data.scenes.new("pytest_profile_b")
    profile = replace(FRAME_16X9_V1, name="custom", frame_width=30, body_font_size=12)
    try:
        window.scene = scene_a
        assert get_profile() == FRAME_16X9_V1
        set_profile(profile)
        assert get_profile() == profile
        assert importlib.reload(state).get_profile() == profile
        monkeypatch.setattr(general, "bpy", SimpleNamespace(data=SimpleNamespace(objects=[], batch_remove=MagicMock())))
        general.clear_scene()
        assert get_profile() == profile
        window.scene = scene_b
        assert get_profile() == FRAME_16X9_V1
        window.scene = scene_a
        assert get_profile() == profile
        reset_profile()
        assert get_profile() == FRAME_16X9_V1
    finally:
        window.scene = original_scene
        bpy.data.scenes.remove(scene_a)
        bpy.data.scenes.remove(scene_b)


def test_invalid_profile_is_rejected():
    with pytest.raises(TypeError, match="VisualProfile"):
        set_profile(None)


def test_profile_survives_saving_and_opening_blend_file(tmp_path):
    blend_path = tmp_path / "profile.blend"
    code = (
        "import bpy; "
        "from dataclasses import replace; "
        "from anima.scene.profile import FRAME_16X9_V1; "
        "from anima.scene.state import get_profile, set_profile; "
        "profile = replace(FRAME_16X9_V1, name='saved', body_font_size=12); "
        "set_profile(profile); "
        f"bpy.ops.wm.save_as_mainfile(filepath={str(blend_path)!r}); "
        f"bpy.ops.wm.open_mainfile(filepath={str(blend_path)!r}); "
        "assert get_profile() == profile"
    )
    subprocess.run([sys.executable, "-c", code], check=True)


def test_background_uses_active_profile(monkeypatch, tmp_path):
    import anima.scene.background as background_module

    textures = MagicMock()
    textures.maps.return_value = {"albedo": tmp_path / "albedo.png"}
    from_directory = MagicMock(return_value=textures)
    rectangle = MagicMock()
    monkeypatch.setattr(background_module.TextureSet, "from_directory", from_directory)
    monkeypatch.setattr(background_module, "Rectangle", rectangle)
    monkeypatch.setattr(background_module, "register_background", MagicMock())
    profile = replace(FRAME_16X9_V1, frame_width=30, texture_tile_size=7, bump_strength=0.3)
    set_profile(profile)
    try:
        background_module.create_background(tmp_path)
        from_directory.assert_called_once_with(tmp_path, physical_size=7)
        rectangle.assert_called_once_with(*profile.background_size, name="Background")
        rectangle.return_value.set_textures.assert_called_once_with(
            textures, bump_strength=0.3, bump_distance=profile.bump_distance
        )
    finally:
        reset_profile()


@pytest.mark.parametrize("override, expected", [(None, 48), (24, 24)])
def test_run_lesson_uses_profile_frame_rate_unless_overridden(monkeypatch, override, expected):
    import anima.runtime as runtime

    monkeypatch.setattr(runtime, "bpy", SimpleNamespace(app=SimpleNamespace(background=True, driver_namespace={})))
    monkeypatch.setattr(runtime, "clear_scene", lambda: None)
    monkeypatch.setattr(runtime, "hide_relationship_lines", lambda: None)
    monkeypatch.setattr(runtime, "deselect_all", lambda: None)
    monkeypatch.setattr(runtime, "Scheduler", MagicMock())
    ebpy = MagicMock()
    monkeypatch.setattr(runtime, "ebpy", ebpy)
    profile = replace(FRAME_16X9_V1, frame_rate=48)
    set_profile(profile)
    try:
        runtime.run_lesson(lambda _start, _end: None, end_time="00:02", frame_rate=override, use_default_lighting=False)
        ebpy.set_render_fps.assert_called_once_with(expected)
    finally:
        reset_profile()


def test_camera_and_lighting_use_active_profile():
    window = bpy.context.window
    original_scene = window.scene
    scene = bpy.data.scenes.new("pytest_profile_setup")
    profile = replace(FRAME_16X9_V1, frame_width=30, camera_height=15, sun_energy=2)
    light = None
    camera = None
    world = None
    try:
        window.scene = scene
        set_profile(profile)
        scene.render.resolution_x, scene.render.resolution_y = profile.preview_resolution
        camera = configure_camera()
        light = configure_lighting()
        world = scene.world
        assert camera.data.ortho_scale == pytest.approx(30)
        assert camera.location.z == pytest.approx(15)
        assert light.data.energy == pytest.approx(2)
    finally:
        window.scene = original_scene
        if light is not None:
            data = light.data
            bpy.data.objects.remove(light, do_unlink=True)
            bpy.data.lights.remove(data)
        if camera is not None:
            data = camera.data
            bpy.data.objects.remove(camera, do_unlink=True)
            bpy.data.cameras.remove(data)
        bpy.data.scenes.remove(scene)
        if world is not None:
            bpy.data.worlds.remove(world)
