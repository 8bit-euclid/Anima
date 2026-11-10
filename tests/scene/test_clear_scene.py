"""Tests for clearing objects during scene reloads."""

import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import anima.globals.general as general


def test_clear_scene_removes_objects_in_one_batch(monkeypatch):
    objects = [object(), object(), object()]
    batch_remove = MagicMock()
    monkeypatch.setattr(
        general, "bpy", SimpleNamespace(data=SimpleNamespace(objects=objects, batch_remove=batch_remove))
    )

    general.clear_scene()

    batch_remove.assert_called_once_with(ids=tuple(objects))


def test_clear_scene_unlinks_objects_from_all_scenes():
    code = """
import bpy
from anima.globals.general import clear_scene

scene = bpy.context.scene
other_scene = bpy.data.scenes.new("other")
mesh = bpy.data.meshes.new("mesh")
shared = bpy.data.objects.new("shared", mesh)
scene.collection.objects.link(shared)
other_scene.collection.objects.link(shared)
camera_data = bpy.data.cameras.new("camera")
camera = bpy.data.objects.new("camera", camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
bpy.data.objects.new("unlinked", None)

clear_scene()
assert len(bpy.data.objects) == 0
assert len(scene.objects) == 0
assert len(other_scene.objects) == 0
assert scene.camera is None
assert bpy.data.meshes.get("mesh") is mesh
assert bpy.data.cameras.get("camera") is camera_data
clear_scene()
"""
    subprocess.run([sys.executable, "-c", code], check=True)
