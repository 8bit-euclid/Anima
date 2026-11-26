"""Tests for inward, in-place curve-loop embossing."""

import bpy
import pytest

from anima.animation.effects import Draw
from anima.latex.glyph import Glyph
from anima.materials.texture import TextureSet
from anima.primitives.chains import CurveLoop
from anima.primitives.curve_emboss import apply_emboss
from anima.primitives.curve_profile import profile_image
from anima.primitives.endcaps import RoundEndcap
from anima.primitives.group import Group
from anima.primitives.lines import Segment
from anima.primitives.polytopes import Rectangle
from anima.utils.render import enable_gpu_devices
from tests.utils.test_utils import create_rect_with_hole_path


def _loop(*, create_joints=False):
    points = [(-1, 0), (1, 0), (1, 1), (-1, 1), (-1, 0)]
    return CurveLoop(
        [Segment(a, b) for a, b in zip(points, points[1:])], width=0.1, bias=0.4, create_joints=create_joints
    )


def test_emboss_modifies_loop_in_place_and_preserves_reveal():
    loop = _loop()
    cap = RoundEndcap(width=0.1, radius=0.05)
    loop.curves[0].attachment_1 = cap
    unrelated = Rectangle(0.1, 0.1)
    loop.add_child(unrelated)
    parent = Group([loop])
    loop.param_1 = 0.7
    object_count = len(bpy.data.objects)
    original_objects = [part.object for part in loop.curves]

    assert apply_emboss(loop, width=0.2, height=lambda t: -0.1 * t) is loop
    assert loop.parent is parent
    assert len(bpy.data.objects) == object_count
    assert [part.object for part in loop.curves] == original_objects
    assert loop.width == pytest.approx(0.2)
    assert loop.bias == -1
    assert loop.param_1 == pytest.approx(0.7)
    for curve in loop.curves:
        assert curve.width == pytest.approx(0.2)
        assert curve.bias == -1
        assert not curve.object.visible_shadow
    assert unrelated.object.visible_shadow
    assert not cap.object.visible_shadow
    Draw(loop).apply(0.35)
    assert loop.param_1 == pytest.approx(0.35)
    loop.validate_param_state()


@pytest.mark.parametrize("width", [0, -1, float("nan"), float("inf")])
def test_emboss_rejects_invalid_width_without_changing_loop(width):
    loop = _loop()
    with pytest.raises(ValueError, match="width"):
        apply_emboss(loop, width=width, height=lambda t: -t)
    assert loop.width == pytest.approx(0.1)
    assert loop.bias == pytest.approx(0.4)
    assert all(profile_image(curve) is None for curve in loop.curves)


def test_emboss_rejects_non_loop():
    with pytest.raises(TypeError, match="CurveLoop"):
        apply_emboss(Segment((0, 0), (1, 0)), width=0.2, height=lambda t: -t)


def test_emboss_rejects_noncallable_height():
    loop = _loop()
    with pytest.raises(TypeError, match="height"):
        apply_emboss(loop, width=0.2, height=None)
    assert loop.width == pytest.approx(0.1)
    assert loop.bias == pytest.approx(0.4)


def test_emboss_rejects_nonfinite_height_without_changing_loop():
    loop = _loop()
    with pytest.raises(ValueError, match="finite"):
        apply_emboss(loop, width=0.2, height=lambda t: float("nan"))
    assert loop.width == pytest.approx(0.1)
    assert loop.bias == pytest.approx(0.4)
    assert all(profile_image(curve) is None for curve in loop.curves)


def test_emboss_preflights_materials_before_changing_geometry():
    loop = _loop()
    loop.set_color((0.2, 0.3, 0.4))
    material = loop.curves[1].object.data.materials[0]
    custom = material.node_tree.nodes.new("ShaderNodeValue")
    material.node_tree.links.new(custom.outputs[0], material.node_tree.nodes["Principled BSDF"].inputs["Normal"])
    with pytest.raises(ValueError, match="custom Normal"):
        apply_emboss(loop, width=0.2, height=lambda t: -t)
    assert loop.width == pytest.approx(0.1)
    assert loop.bias == pytest.approx(0.4)
    assert all(curve.object.visible_shadow for curve in loop.curves)
    assert profile_image(loop.curves[0]) is None


@pytest.mark.parametrize("width", [0.18, 0.09, 0.045])
def test_emboss_applies_to_round_joints(width):
    loop = _loop(create_joints=True)
    loop.set_color((0.6, 0.6, 0.6))
    apply_emboss(loop, width=width, height=lambda t: -0.06 * t * t * (3 - 2 * t))
    for joint in loop._joints:
        assert joint.width == pytest.approx(width)
        assert joint.bias == -1
        assert profile_image(joint) is not None
        assert joint.object.data.polygons
        assert not joint.object.visible_shadow
    loop.validate_param_state()


@pytest.mark.parametrize("with_joint", [False, True])
def test_emboss_profile_changes_inward_lighting_on_textured_surface_cycles_gpu(tmp_path, with_joint):
    try:
        enable_gpu_devices()
    except RuntimeError as error:
        pytest.skip(str(error))

    image = bpy.data.images.new("emboss_texture", width=16, height=2)
    image.colorspace_settings.name = "Non-Color"
    pixels = []
    for _ in range(2):
        for x in range(16):
            value = 0.2 + 0.5 * x / 15
            pixels.extend((value, value, value, 1))
    image.pixels = pixels
    image.filepath_raw = str(tmp_path / "texture.png")
    image.file_format = "PNG"
    image.save()
    bpy.data.images.remove(image)
    textures = TextureSet(height=tmp_path / "texture.png", physical_size=(4, 4))

    loop = _loop(create_joints=with_joint)
    paper = Rectangle(4, 4)
    for obj in (paper, loop):
        obj.set_color((0.6, 0.6, 0.6))
        obj.set_textures(textures, bump_strength=0.3, bump_distance=0.03)
    paper.layer = -1
    scene = bpy.data.scenes.new("emboss_test_scene")
    camera_data = bpy.data.cameras.new("emboss_test_camera")
    camera = bpy.data.objects.new("emboss_test_camera", camera_data)
    light_data = bpy.data.lights.new("emboss_test_light", type="SUN")
    light = bpy.data.objects.new("emboss_test_light", light_data)
    for obj in (paper.object, loop.curves[0].object, camera, light):
        scene.collection.objects.link(obj)
    if with_joint:
        scene.collection.objects.link(loop._joints[0].object)
    camera.location = (0.8 if with_joint else 0, 0.2, 5)
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 2
    scene.camera = camera
    light.rotation_euler = (0.8, 0, 0)
    light_data.energy = 2
    scene.render.engine = "CYCLES"
    scene.cycles.device = "GPU"
    scene.cycles.samples = 64
    scene.cycles.use_denoising = False
    scene.render.resolution_x = scene.render.resolution_y = 192
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "Standard"
    try:
        results = []
        for depth in (-0.12, 0.12):
            apply_emboss(loop, width=0.4, height=lambda t, depth=depth: depth * t * t * (3 - 2 * t))
            scene.render.filepath = str(tmp_path / f"emboss_{depth}.png")
            bpy.ops.render.render(scene=scene.name, write_still=True)
            image = bpy.data.images.load(scene.render.filepath, check_existing=False)
            rendered = list(image.pixels)
            bpy.data.images.remove(image)
            rows = [int((y - camera.location.y) / 2 * 192 + 96) for y in (-0.2, 0.2, 0.6)]
            results.append([rendered[4 * (row * 192 + 96)] for row in rows])

        recessed, raised = results
        assert raised[1] > recessed[1] + 0.08
        assert recessed[0] == pytest.approx(raised[0], abs=0.03)
        assert recessed[2] == pytest.approx(raised[2], abs=0.03)
    finally:
        bpy.data.scenes.remove(scene)
        bpy.data.objects.remove(camera, do_unlink=True)
        bpy.data.cameras.remove(camera_data)
        bpy.data.objects.remove(light, do_unlink=True)
        bpy.data.lights.remove(light_data)


def test_emboss_follows_glyph_outer_and_hole_winding_on_cycles_gpu(tmp_path):
    try:
        enable_gpu_devices()
    except RuntimeError as error:
        pytest.skip(str(error))

    paper = Rectangle(30, 30, location=(10, -10, 0))
    paper.set_color((0.6, 0.6, 0.6))
    paper.layer = -1
    glyph = Glyph(create_rect_with_hole_path().reversed(), with_border=True)
    glyph.set_color((0.6, 0.6, 0.6))
    glyph.body.object.visible_shadow = False
    for boundary in glyph.border.subpaths:
        boundary.layer = 1

    scene = bpy.data.scenes.new("emboss_glyph_scene")
    camera_data = bpy.data.cameras.new("emboss_glyph_camera")
    camera = bpy.data.objects.new("emboss_glyph_camera", camera_data)
    light_data = bpy.data.lights.new("emboss_glyph_light", type="SUN")
    light = bpy.data.objects.new("emboss_glyph_light", light_data)
    for obj in (paper.object, camera, light):
        scene.collection.objects.link(obj)
    pending = [glyph]
    while pending:
        obj = pending.pop()
        scene.collection.objects.link(obj.object)
        pending.extend(obj.children)
    camera.location = (10, -10, 30)
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 25
    scene.camera = camera
    light.rotation_euler = (0.8, 0, 0)
    light_data.energy = 2
    scene.render.engine = "CYCLES"
    scene.cycles.device = "GPU"
    scene.cycles.samples = 64
    scene.cycles.use_denoising = False
    scene.render.resolution_x = scene.render.resolution_y = 200
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "Standard"
    try:
        results = []
        for depth in (-0.3, 0.3):
            for boundary in glyph.border.subpaths:
                apply_emboss(boundary, width=1, height=lambda t, depth=depth: depth * t * t * (3 - 2 * t))
            scene.render.filepath = str(tmp_path / f"emboss_glyph_{depth}.png")
            bpy.ops.render.render(scene=scene.name, write_still=True)
            image = bpy.data.images.load(scene.render.filepath, check_existing=False)
            pixels = list(image.pixels)
            bpy.data.images.remove(image)
            rows = [int((y + 10) / 25 * 200 + 100) for y in (-0.5, -4.5, -10)]
            results.append([pixels[4 * (row * 200 + 100)] for row in rows])

        recessed, raised = results
        outer_difference = raised[0] - recessed[0]
        hole_difference = raised[1] - recessed[1]
        assert abs(outer_difference) > 0.08
        assert abs(hole_difference) > 0.08
        assert outer_difference * hole_difference < 0
        assert recessed[2] == pytest.approx(raised[2], abs=0.03)
    finally:
        bpy.data.scenes.remove(scene)
        bpy.data.objects.remove(camera, do_unlink=True)
        bpy.data.cameras.remove(camera_data)
        bpy.data.objects.remove(light, do_unlink=True)
        bpy.data.lights.remove(light_data)
