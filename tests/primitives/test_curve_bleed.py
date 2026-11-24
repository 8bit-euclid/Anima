"""Tests for in-place curve-loop bleed."""

import subprocess
import sys

import bpy
import pytest

from anima.animation.effects import Draw
from anima.latex.glyph import Glyph
from anima.primitives.chains import CurveLoop
from anima.primitives.curve_bleed import apply_bleed
from anima.primitives.curve_profile import profile_image
from anima.primitives.endcaps import RoundEndcap
from anima.primitives.group import Group
from anima.primitives.lines import Segment
from anima.primitives.polytopes import Rectangle
from anima.utils.render import enable_gpu_devices
from tests.utils.test_utils import create_rect_with_hole_path


def _loop():
    points = [(-1, 0), (1, 0), (1, 1), (-1, 1), (-1, 0)]
    return CurveLoop([Segment(a, b) for a, b in zip(points, points[1:])], width=0.1, bias=0.4)


@pytest.mark.parametrize("bias", [-0.8, 0.0, 0.99, 1.0])
def test_bleed_modifies_loop_in_place_and_follows_draw(bias):
    loop = _loop()
    unrelated = Rectangle(0.1, 0.1)
    loop.add_child(unrelated)
    parent = Group([loop])
    loop.param_1 = 0.7
    object_count = len(bpy.data.objects)
    original_objects = [part.object for part in loop.curves]

    assert apply_bleed(loop, width=0.4, bias=bias) is loop
    assert loop.parent is parent
    assert len(bpy.data.objects) == object_count
    assert [part.object for part in loop.curves] == original_objects
    assert loop.width == pytest.approx(0.8 / (1 + bias))
    assert loop.bias == bias
    assert loop.param_1 == pytest.approx(0.7)
    for curve in loop.curves:
        assert curve.width == pytest.approx(loop.width)
        assert curve.bias == bias
    assert unrelated.object.visible_shadow

    Draw(loop).apply(0.35)
    assert loop.param_1 == pytest.approx(0.35)
    loop.validate_param_state()


def test_bleed_defaults_to_nearly_outward_bias():
    loop = _loop()
    apply_bleed(loop, width=0.4)
    assert loop.bias == pytest.approx(0.99)
    assert loop.width == pytest.approx(0.8 / 1.99)


@pytest.mark.parametrize("width", [0, -1, float("nan"), float("inf"), 1e308])
def test_bleed_rejects_invalid_width_without_changing_loop(width):
    loop = _loop()
    with pytest.raises(ValueError, match="width"):
        apply_bleed(loop, width=width, bias=0)
    assert loop.width == pytest.approx(0.1)
    assert loop.bias == pytest.approx(0.4)
    assert all(profile_image(curve) is None for curve in loop.curves)


@pytest.mark.parametrize("bias", [-1, -2, 1.01, float("nan"), float("inf"), -float("inf"), True])
def test_bleed_rejects_invalid_bias_without_changing_loop(bias):
    loop = _loop()
    with pytest.raises(ValueError, match="bias"):
        apply_bleed(loop, width=0.4, bias=bias)
    assert loop.width == pytest.approx(0.1)
    assert loop.bias == pytest.approx(0.4)
    assert all(profile_image(curve) is None for curve in loop.curves)


def test_bleed_rejects_non_loop():
    with pytest.raises(TypeError, match="CurveLoop"):
        apply_bleed(Segment((0, 0), (1, 0)), width=0.2)


def test_bleed_preflights_materials_before_changing_geometry():
    loop = _loop()
    loop.set_color((0.2, 0.3, 0.4))
    material = loop.curves[1].object.data.materials[0]
    custom = material.node_tree.nodes.new("ShaderNodeValue")
    material.node_tree.links.new(custom.outputs[0], material.node_tree.nodes["Principled BSDF"].inputs["Alpha"])

    with pytest.raises(ValueError, match="custom Alpha"):
        apply_bleed(loop, width=0.2)
    assert loop.width == pytest.approx(0.1)
    assert loop.bias == pytest.approx(0.4)
    assert all(curve.object.visible_shadow for curve in loop.curves)
    assert profile_image(loop.curves[0]) is None


@pytest.mark.parametrize("cap", [False, True])
@pytest.mark.parametrize("bias", [-0.8, 0.0, 0.99, 1.0])
def test_bleed_has_opaque_overlap_and_outward_fade_on_cycles_gpu(tmp_path, cap, bias):
    try:
        enable_gpu_devices()
    except RuntimeError as error:
        pytest.skip(str(error))
    loop = _loop()
    loop.set_material_properties(color=(1, 1, 1), emission_strength=1.0, opacity=1.0)
    apply_bleed(loop, width=0.4, bias=bias)
    curve = loop.curves[0]
    if cap:
        curve.attachment_1 = RoundEndcap(width=loop.width, radius=loop.width / 2)
        bpy.context.view_layer.update()
    scene = bpy.data.scenes.new("bleed_test_scene")
    camera_data = bpy.data.cameras.new("bleed_test_camera")
    camera = bpy.data.objects.new("bleed_test_camera", camera_data)
    scene.collection.objects.link(camera)
    scene.collection.objects.link(curve.attachment_1.object if cap else curve.object)
    camera.location = (1.05 if cap else 0, -0.2, 5)
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 0.8
    scene.camera = camera
    scene.render.engine = "CYCLES"
    scene.cycles.device = "GPU"
    scene.cycles.samples = 128
    scene.cycles.use_denoising = False
    scene.render.film_transparent = True
    scene.render.resolution_x = scene.render.resolution_y = 256
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.filepath = str(tmp_path / f"bleed_{cap}.png")
    try:
        bpy.ops.render.render(scene=scene.name, write_still=True)
        image = bpy.data.images.load(scene.render.filepath, check_existing=False)
        pixels = list(image.pixels)
        bpy.data.images.remove(image)
        positions = (-0.1, -0.3, -0.5)
        rows = [int((y - camera.location.y) / 0.8 * 256 + 128) for y in positions]
        alpha = [pixels[4 * (row * 256 + 128) + 3] for row in rows]
        assert alpha == pytest.approx((0.75, 0.25, 0.0), abs=0.13)
        if bias <= 0:
            row = int((0.1 - camera.location.y) / 0.8 * 256 + 128)
            assert pixels[4 * (row * 256 + 128) + 3] == pytest.approx(1.0, abs=0.13)
    finally:
        bpy.data.scenes.remove(scene)
        bpy.data.objects.remove(camera, do_unlink=True)
        bpy.data.cameras.remove(camera_data)


def test_bleed_renders_outside_a_glyph_and_inside_its_hole_on_cycles_gpu(tmp_path):
    try:
        enable_gpu_devices()
    except RuntimeError as error:
        pytest.skip(str(error))
    glyph = Glyph(create_rect_with_hole_path().reversed(), with_border=True)
    glyph.set_material_properties(color=(1, 1, 1), emission_strength=1.0, opacity=1.0)
    for boundary in glyph.border.subpaths:
        apply_bleed(boundary, width=2.0)
        boundary.layer = -1

    scene = bpy.data.scenes.new("bleed_glyph_scene")
    camera_data = bpy.data.cameras.new("bleed_glyph_camera")
    camera = bpy.data.objects.new("bleed_glyph_camera", camera_data)
    scene.collection.objects.link(camera)
    pending = [glyph]
    while pending:
        obj = pending.pop()
        scene.collection.objects.link(obj.object)
        pending.extend(obj.children)
    camera.location = (10, -10, 5)
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 30.0
    scene.camera = camera
    scene.render.engine = "CYCLES"
    scene.cycles.device = "GPU"
    scene.cycles.samples = 128
    scene.cycles.use_denoising = False
    scene.render.film_transparent = True
    scene.render.resolution_x = scene.render.resolution_y = 240
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.filepath = str(tmp_path / "bleed_glyph.png")
    try:
        bpy.ops.render.render(scene=scene.name, write_still=True)
        image = bpy.data.images.load(scene.render.filepath, check_existing=False)
        pixels = list(image.pixels)
        bpy.data.images.remove(image)

        def alpha(x, y):
            column = int((x - 10) / 30 * 240 + 120)
            row = int((y + 10) / 30 * 240 + 120)
            return pixels[4 * (row * 240 + column) + 3]

        assert alpha(2, -10) == pytest.approx(1.0, abs=0.1)
        assert alpha(10, -10) == pytest.approx(0.0, abs=0.1)
        assert alpha(10, 0.5) == pytest.approx(0.75, abs=0.15)
        assert alpha(10, 1.5) == pytest.approx(0.25, abs=0.15)
        assert alpha(10, -5.5) == pytest.approx(0.75, abs=0.15)
        assert alpha(10, -6.5) == pytest.approx(0.25, abs=0.15)
    finally:
        bpy.data.scenes.remove(scene)
        bpy.data.objects.remove(camera, do_unlink=True)
        bpy.data.cameras.remove(camera_data)


def test_bleed_does_not_cast_corner_shadows_on_cycles_gpu(tmp_path):
    try:
        enable_gpu_devices()
    except RuntimeError as error:
        pytest.skip(str(error))
    path = tmp_path / "bleed_gallery.png"
    subprocess.run([sys.executable, "-m", "tests.visual_tests.test_curve_bleed", str(path)], check=True)
    image = bpy.data.images.load(str(path), check_existing=False)
    try:
        assert image.pixels[4 * (554 * 1200 + 609)] > 0.44
    finally:
        bpy.data.images.remove(image)
