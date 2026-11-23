"""Tests for sampled curve-width profiles."""

import subprocess
import sys

import bpy
import pytest
from mathutils import Vector

from anima.animation.effects import Fade
from anima.materials.curve_profile import PROFILE_ALPHA, PROFILE_BUMP, PROFILE_UV
from anima.materials.texture import TEXTURE_GROUP_NODE, TextureSet, remove_texture_nodes
from anima.primitives.chains import CurveChain
from anima.primitives.curve_profile import profile_image
from anima.primitives.endcaps import RoundEndcap
from anima.primitives.lines import Segment
from anima.utils.render import enable_gpu_devices


def _material(curve):
    return curve.object.data.materials[0]


def _source(material, socket):
    return material.node_tree.nodes["Principled BSDF"].inputs[socket].links[0].from_node


@pytest.mark.parametrize(
    ("height", "opacity", "samples"),
    [
        (None, None, 4),
        (lambda u: float("nan"), None, 4),
        (None, lambda u: 1.1, 4),
        (None, lambda u: -0.1, 4),
        (None, lambda u: u, 1),
    ],
)
def test_invalid_profiles_are_rejected_without_changing_material(height, opacity, samples):
    curve = Segment((0, 0), (1, 0))
    curve.set_color((0.2, 0.3, 0.4))
    with pytest.raises(ValueError):
        curve.set_width_profile(height=height, opacity=opacity, samples=samples)
    assert not _material(curve).node_tree.nodes.get(PROFILE_ALPHA)


def test_custom_shader_link_rejects_profile_without_partially_styling_chain():
    first = Segment((0, 0), (1, 0))
    second = Segment((1, 0), (2, 0))
    chain = CurveChain([first, second], create_joints=False)
    chain.set_color((0.2, 0.3, 0.4))
    mat = _material(second)
    custom = mat.node_tree.nodes.new("ShaderNodeValue")
    mat.node_tree.links.new(custom.outputs[0], mat.node_tree.nodes["Principled BSDF"].inputs["Alpha"])
    with pytest.raises(ValueError, match="custom Alpha"):
        chain.set_width_profile(opacity=lambda u: u)
    assert not _material(first).node_tree.nodes.get(PROFILE_ALPHA)
    assert not _material(chain).node_tree.nodes.get(PROFILE_ALPHA)
    assert _source(mat, "Alpha") == custom


@pytest.mark.parametrize("texture_first", [False, True])
def test_profile_composes_with_texture_reveal_fade_and_removal(tmp_path, texture_first):
    image = bpy.data.images.new("profile_test_height", 4, 1)
    image.colorspace_settings.name = "Non-Color"
    image.pixels = [channel for h in (0.0, 0.3, 0.7, 1.0) for channel in (h, h, h, 1.0)]
    image.filepath_raw = str(tmp_path / "height.png")
    image.file_format = "PNG"
    image.save()
    bpy.data.images.remove(image)
    textures = TextureSet(height=tmp_path / "height.png")
    curve = Segment((0, 0), (1, 0))
    curve.set_opacity(0.7)
    if texture_first:
        curve.set_textures(textures, height_reveal=(0.0, 1.0))
    curve.set_width_profile(height=lambda u: 0.02 * u, opacity=lambda u: u)
    if not texture_first:
        curve.set_textures(textures, height_reveal=(0.0, 1.0))
    mat = _material(curve)
    texture = mat.node_tree.nodes[TEXTURE_GROUP_NODE]
    alpha, bump = _source(mat, "Alpha"), _source(mat, "Normal")
    assert alpha.name == PROFILE_ALPHA
    assert bump.name == PROFILE_BUMP
    assert alpha.inputs[0].links[0].from_node == texture
    assert bump.inputs["Normal"].links[0].from_node == texture
    Fade(curve).apply(0.3)
    assert curve.opacity == pytest.approx(0.3)
    assert texture.inputs["Native Opacity"].default_value == pytest.approx(0.3)
    curve.set_textures(textures, height_reveal=(0.0, 1.0))
    assert _source(mat, "Alpha").name == PROFILE_ALPHA
    assert _source(mat, "Normal").name == PROFILE_BUMP
    remove_texture_nodes(mat)
    assert _source(mat, "Alpha").inputs[0].default_value == pytest.approx(0.3)
    curve.set_textures(textures, height_reveal=(0.0, 1.0))
    curve.clear_width_profile()
    assert _source(mat, "Alpha").name == TEXTURE_GROUP_NODE
    assert _source(mat, "Normal").name == TEXTURE_GROUP_NODE


@pytest.mark.parametrize("end_y", [1, -1])
def test_joint_and_endcap_coordinates_survive_geometry_updates(end_y):
    first = Segment((0, 0), (1, 0))
    second = Segment((1, 0), (1, end_y))
    chain = CurveChain([first, second], width=0.2)
    first.attachment_0 = RoundEndcap(width=0.2, radius=0.1)
    chain.set_width_profile(opacity=lambda u: u)
    joint = chain._joints[0]
    chain.width = 0.3
    chain.param_1 = 0.7
    mesh = joint.object.data
    uv = mesh.uv_layers["UVMap"]
    for loop in mesh.loops:
        expected = (
            (1.0 if joint._orientation > 0 else 0.0)
            if loop.vertex_index == 0
            else (0.0 if joint._orientation > 0 else 1.0)
        )
        assert uv.data[loop.index].uv.y == pytest.approx(expected)
    cap = first.attachment_0.object.data
    cap_uv = cap.uv_layers[PROFILE_UV]
    for loop in cap.loops:
        x = cap.vertices[loop.vertex_index].co.x
        assert cap_uv.data[loop.index].uv.y == pytest.approx(0.5 - x / 0.3)


def test_dashes_and_later_endcaps_inherit_profile():
    curve = Segment((0, 0), (2, 0), width=0.2)
    curve.set_width_profile(opacity=lambda u: u)
    curve.attachment_1 = RoundEndcap(width=0.2, radius=0.1)
    assert _source(_material(curve.attachment_1), "Alpha").name == PROFILE_ALPHA
    dashed = curve.make_dashed(dash_len=0.4, gap_len=0.2)
    for dash in dashed._dashes:
        assert _source(_material(dash.curve), "Alpha").name == PROFILE_ALPHA


def test_later_endcap_uses_current_shared_material_profile():
    first = Segment((0, 0), (1, 0), width=0.2)
    second = Segment((0, 1), (1, 1), width=0.2)
    first.set_opacity(1.0)
    second.set_opacity(1.0)
    second.object.data.materials[0] = _material(first)
    first.set_width_profile(opacity=lambda u: 0.2, samples=2)
    second.set_width_profile(opacity=lambda u: 0.8, samples=2)

    first.attachment_1 = RoundEndcap(width=0.2, radius=0.1)
    curve_image = profile_image(first)
    cap_image = profile_image(first.attachment_1)
    assert cap_image.pixels[1] == pytest.approx(curve_image.pixels[1])
    assert cap_image.pixels[1] == pytest.approx(0.8)


def test_endcap_inherits_profile_added_via_shared_material():
    first = Segment((0, 0), (1, 0), width=0.2)
    second = Segment((0, 1), (1, 1), width=0.2)
    first.set_opacity(1.0)
    second.set_opacity(1.0)
    second.object.data.materials[0] = _material(first)
    first.set_width_profile(opacity=lambda u: 0.7, samples=2)

    second.attachment_1 = RoundEndcap(width=0.2, radius=0.1)
    image = profile_image(second.attachment_1)
    assert image.pixels[1] == pytest.approx(0.7)


def test_endcap_does_not_inherit_removed_shared_profile():
    first = Segment((0, 0), (1, 0), width=0.2)
    second = Segment((0, 1), (1, 1), width=0.2)
    first.set_opacity(1.0)
    second.set_opacity(1.0)
    second.object.data.materials[0] = _material(first)
    first.set_width_profile(opacity=lambda u: 0.7, samples=2)
    second.clear_width_profile()

    first.attachment_1 = RoundEndcap(width=0.2, radius=0.1)
    materials = first.attachment_1.object.data.materials
    assert not materials or not materials[0].node_tree.nodes.get(PROFILE_ALPHA)


def test_existing_endcap_follows_shared_profile_update_clear_and_reapply():
    first = Segment((0, 0), (1, 0), width=0.2)
    second = Segment((0, 1), (1, 1), width=0.2)
    first.set_opacity(1.0)
    second.set_opacity(1.0)
    second.object.data.materials[0] = _material(first)
    first.set_width_profile(opacity=lambda u: 0.2, samples=2)
    first.attachment_1 = RoundEndcap(width=0.2, radius=0.1)

    second.set_width_profile(height=lambda u: 0.1 * u, opacity=lambda u: 0.8, samples=7)
    assert profile_image(first.attachment_1).pixels[1] == pytest.approx(0.8)
    assert profile_image(first.attachment_1).pixels[-4] == pytest.approx(0.1)
    assert tuple(profile_image(first.attachment_1).size) == (7, 1)

    second.clear_width_profile()
    assert profile_image(first) is None
    assert profile_image(first.attachment_1) is None

    second.set_width_profile(opacity=lambda u: 0.4, samples=3)
    assert profile_image(first.attachment_1).pixels[1] == pytest.approx(0.4)


def test_existing_endcap_follows_profile_added_via_shared_material():
    first = Segment((0, 0), (1, 0), width=0.2)
    second = Segment((0, 1), (1, 1), width=0.2)
    first.set_opacity(1.0)
    second.set_opacity(1.0)
    second.object.data.materials[0] = _material(first)
    first.attachment_1 = RoundEndcap(width=0.2, radius=0.1)
    first.width = 0.4

    second.set_width_profile(opacity=lambda u: 0.6)
    assert profile_image(first.attachment_1).pixels[1] == pytest.approx(0.6)
    mesh = first.attachment_1.object.data
    for loop in mesh.loops:
        x = mesh.vertices[loop.vertex_index].co.x
        assert mesh.uv_layers[PROFILE_UV].data[loop.index].uv.y == pytest.approx(0.5 + x / 0.4)


def test_endcap_profile_preserves_existing_uv_map():
    curve = Segment((0, 0), (1, 0), width=0.2)
    cap = RoundEndcap(width=0.2, radius=0.1)
    uv = cap.object.data.uv_layers.new(name="UVMap")
    for loop in uv.data:
        loop.uv = (0.25, 0.75)
    curve.attachment_1 = cap
    curve.set_width_profile(opacity=lambda u: u)
    curve.width = 0.4

    assert all(tuple(loop.uv) == pytest.approx((0.25, 0.75)) for loop in uv.data)
    assert _material(cap).node_tree.nodes["anima_curve_profile_uv"].uv_map == PROFILE_UV


def test_endcap_can_share_curve_material():
    curve = Segment((0, 0), (1, 0), width=0.2)
    curve.set_opacity(1.0)
    cap = RoundEndcap(width=0.2, radius=0.1)
    cap.object.data.materials.append(_material(curve))
    curve.attachment_1 = cap
    curve.set_width_profile(opacity=lambda u: u)
    curve.width = 0.4

    assert _material(cap) == _material(curve)
    assert _material(cap).node_tree.nodes["anima_curve_profile_uv"].uv_map == "UVMap"
    mesh = cap.object.data
    for loop in mesh.loops:
        x = mesh.vertices[loop.vertex_index].co.x
        assert mesh.uv_layers["UVMap"].data[loop.index].uv.y == pytest.approx(0.5 + x / 0.4)


def test_shared_profile_validation_includes_existing_endcaps():
    first = Segment((0, 0), (1, 0), width=0.2)
    second = Segment((0, 1), (1, 1), width=0.2)
    first.set_opacity(1.0)
    second.set_opacity(1.0)
    second.object.data.materials[0] = _material(first)
    first.attachment_1 = RoundEndcap(width=0.2, radius=0.1)
    cap_material = _material(first.attachment_1)
    custom = cap_material.node_tree.nodes.new("ShaderNodeValue")
    cap_material.node_tree.links.new(custom.outputs[0], cap_material.node_tree.nodes["Principled BSDF"].inputs["Alpha"])

    with pytest.raises(ValueError, match="custom Alpha"):
        second.set_width_profile(opacity=lambda u: u)
    assert profile_image(first) is None
    assert _source(cap_material, "Alpha") == custom


def test_shared_profile_preserves_endcap_color_and_texture(tmp_path):
    image = bpy.data.images.new("endcap_height", 2, 1)
    image.pixels = [0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0]
    image.filepath_raw = str(tmp_path / "endcap_height.png")
    image.file_format = "PNG"
    image.save()
    bpy.data.images.remove(image)
    first = Segment((0, 0), (1, 0), width=0.2)
    second = Segment((0, 1), (1, 1), width=0.2)
    first.set_opacity(1.0)
    second.set_opacity(1.0)
    second.object.data.materials[0] = _material(first)
    cap = RoundEndcap(width=0.2, radius=0.1)
    cap.set_color((0.2, 0.3, 0.4))
    cap.set_textures(TextureSet(height=tmp_path / "endcap_height.png"))
    first.attachment_1 = cap
    material = _material(cap)
    texture = material.node_tree.nodes[TEXTURE_GROUP_NODE]
    color = tuple(material.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value)

    second.set_width_profile(height=lambda u: 0.1 * u, opacity=lambda u: u)
    assert _source(material, "Normal").inputs["Normal"].links[0].from_node == texture
    assert tuple(material.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value) == pytest.approx(color)
    second.clear_width_profile()
    assert _source(material, "Normal") == texture
    assert tuple(material.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value) == pytest.approx(color)


def test_unstyled_attachment_does_not_reuse_unrelated_named_materials():
    curve = Segment((0, 0), (1, 0), width=0.2, name="profile_unique_curve")
    cap = RoundEndcap(width=0.2, radius=0.1, name="profile_unique_cap")
    unrelated = Segment((0, 1), (1, 1), width=0.2)
    unrelated.set_width_profile(opacity=lambda u: 0.3)
    unrelated_material = _material(unrelated)
    unrelated_material.name = f"{cap.name}_material"

    curve.attachment_1 = cap
    curve.set_width_profile(opacity=lambda u: 0.8)

    assert _material(cap) != unrelated_material
    assert profile_image(unrelated).pixels[1] == pytest.approx(0.3)


def test_profiled_copy_and_its_endcap_are_independent():
    original = Segment((0, 0), (1, 0), width=0.2)
    original.attachment_1 = RoundEndcap(width=0.2, radius=0.1)
    original.set_width_profile(opacity=lambda u: 0.2, samples=2)
    copied = original.copy()
    peer = Segment((0, 1), (1, 1), width=0.2)
    peer.set_opacity(1.0)
    peer.object.data.materials[0] = _material(copied)

    peer.set_width_profile(opacity=lambda u: 0.8, samples=3)
    assert profile_image(original).pixels[1] == pytest.approx(0.2)
    assert profile_image(original.attachment_1).pixels[1] == pytest.approx(0.2)
    assert profile_image(copied).pixels[1] == pytest.approx(0.8)
    assert profile_image(copied.attachment_1).pixels[1] == pytest.approx(0.8)
    original.clear_width_profile()
    assert profile_image(original.attachment_1) is None
    assert profile_image(copied.attachment_1).pixels[1] == pytest.approx(0.8)


def test_dashes_are_independent_of_later_original_profile_changes():
    curve = Segment((0, 0), (2, 0), width=0.2)
    curve.set_width_profile(opacity=lambda u: 0.2, samples=2)
    dashed = curve.make_dashed(dash_len=0.4, gap_len=0.2)
    curve.set_width_profile(opacity=lambda u: 0.8, samples=3)

    for dash in dashed._dashes:
        assert profile_image(dash.curve).pixels[1] == pytest.approx(0.2)


def test_width_coordinate_tracks_width_and_bias():
    curve = Segment((0, 0), (2, 0), width=0.4)
    curve.set_width_profile(opacity=lambda u: u)
    curve.width = 0.8
    curve.bias = -0.5
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = curve.object.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
    try:
        uv = mesh.uv_layers["UVMap"]
        for loop in mesh.loops:
            y = mesh.vertices[loop.vertex_index].co.y
            assert uv.data[loop.index].uv.y == pytest.approx(0.5 - (y - 0.2) / 0.8, abs=1e-5)
    finally:
        evaluated.to_mesh_clear()


def test_shared_endcap_profile_changes_render_on_cycles_gpu(tmp_path):
    try:
        enable_gpu_devices()
    except RuntimeError as error:
        pytest.skip(str(error))
    first = Segment((-1, 0), (0, 0), width=1.0)
    second = Segment((-1, 1), (0, 1), width=1.0)
    first.set_opacity(1.0)
    second.set_opacity(1.0)
    second.object.data.materials[0] = _material(first)
    first.attachment_1 = RoundEndcap(width=1.0, radius=0.5)
    cap = first.attachment_1
    cap.set_material_properties(color=(1.0, 1.0, 1.0), emission_strength=1.0)
    bpy.context.view_layer.update()

    scene = bpy.data.scenes.new("profile_endcap_scene")
    camera_data = bpy.data.cameras.new("profile_endcap_camera")
    camera = bpy.data.objects.new("profile_endcap_camera", camera_data)
    scene.collection.objects.link(camera)
    scene.collection.objects.link(cap.object)
    center = cap.object.matrix_world @ Vector((0, 0.2, 0))
    camera.location = (center.x, center.y, 5)
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 0.1
    scene.camera = camera
    scene.render.engine = "CYCLES"
    scene.cycles.device = "GPU"
    scene.cycles.samples = 128
    scene.cycles.use_denoising = False
    scene.render.film_transparent = True
    scene.render.resolution_x = scene.render.resolution_y = 16
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.filepath = str(tmp_path / "endcap.png")
    try:
        for opacity in (0.2, 0.8, None, 0.4):
            if opacity is None:
                second.clear_width_profile()
            else:
                second.set_width_profile(opacity=lambda u, value=opacity: value, samples=3)
            bpy.ops.render.render(scene=scene.name, write_still=True)
            image = bpy.data.images.load(scene.render.filepath, check_existing=False)
            alpha = image.pixels[4 * (8 * 16 + 8) + 3]
            bpy.data.images.remove(image)
            assert alpha == pytest.approx(1.0 if opacity is None else opacity, abs=0.15)
    finally:
        bpy.data.scenes.remove(scene)
        bpy.data.objects.remove(camera, do_unlink=True)
        bpy.data.cameras.remove(camera_data)


def test_opacity_profile_renders_on_cycles_gpu(tmp_path):
    try:
        enable_gpu_devices()
    except RuntimeError as error:
        pytest.skip(str(error))
    curve = Segment((-1, 0), (1, 0), width=1.0)
    curve.set_material_properties(color=(1.0, 1.0, 1.0), emission_strength=1.0, opacity=0.5)
    curve.set_width_profile(opacity=lambda u: u)
    curve.param_0, curve.param_1 = 0.2, 0.8
    scene = bpy.data.scenes.new("profile_test_scene")
    camera_data = bpy.data.cameras.new("profile_test_camera")
    camera = bpy.data.objects.new("profile_test_camera", camera_data)
    scene.collection.objects.link(camera)
    scene.collection.objects.link(curve.object)
    camera.location = (0, 0, 5)
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 2.0
    scene.camera = camera
    scene.render.engine = "CYCLES"
    scene.cycles.device = "GPU"
    scene.cycles.samples = 128
    scene.cycles.use_denoising = False
    scene.render.film_transparent = True
    scene.render.resolution_x = scene.render.resolution_y = 64
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.filepath = str(tmp_path / "profile.png")
    try:
        bpy.ops.render.render(scene=scene.name, write_still=True)
        image = bpy.data.images.load(scene.render.filepath, check_existing=False)
        pixels = list(image.pixels)
        bpy.data.images.remove(image)
        # Looking along +X, the upper edge is left (u=0) and lower is right (u=1).
        lower = pixels[4 * (24 * 64 + 32) + 3]
        upper = pixels[4 * (40 * 64 + 32) + 3]
        assert lower == pytest.approx(0.37, abs=0.10)
        assert upper == pytest.approx(0.12, abs=0.10)
    finally:
        bpy.data.scenes.remove(scene)
        bpy.data.objects.remove(camera, do_unlink=True)
        bpy.data.cameras.remove(camera_data)


def test_height_profile_changes_lighting_on_cycles_gpu(tmp_path):
    try:
        enable_gpu_devices()
    except RuntimeError as error:
        pytest.skip(str(error))
    flat = Segment((-1, 0.6), (1, 0.6), width=0.5)
    raised = Segment((-1, -0.6), (1, -0.6), width=0.5)
    flat.set_color((0.6, 0.6, 0.6))
    raised.set_color((0.6, 0.6, 0.6))
    raised.set_width_profile(height=lambda u: 0.25 * u)
    scene = bpy.data.scenes.new("profile_bump_scene")
    camera_data = bpy.data.cameras.new("profile_bump_camera")
    camera = bpy.data.objects.new("profile_bump_camera", camera_data)
    light_data = bpy.data.lights.new("profile_bump_light", type="SUN")
    light = bpy.data.objects.new("profile_bump_light", light_data)
    for obj in (flat.object, raised.object, camera, light):
        scene.collection.objects.link(obj)
    camera.location = (0, 0, 5)
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 3.0
    scene.camera = camera
    light.rotation_euler = (0.8, 0, 0)
    light_data.energy = 2.0
    scene.render.engine = "CYCLES"
    scene.cycles.device = "GPU"
    scene.cycles.samples = 32
    scene.cycles.use_denoising = False
    scene.render.resolution_x = scene.render.resolution_y = 64
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "Standard"
    scene.render.filepath = str(tmp_path / "bump.png")
    try:
        bpy.ops.render.render(scene=scene.name, write_still=True)
        image = bpy.data.images.load(scene.render.filepath, check_existing=False)
        pixels = list(image.pixels)
        bpy.data.images.remove(image)
        flat_value = pixels[4 * (45 * 64 + 32)]
        bump_value = pixels[4 * (19 * 64 + 32)]
        assert abs(bump_value - flat_value) > 0.08
    finally:
        bpy.data.scenes.remove(scene)
        bpy.data.objects.remove(camera, do_unlink=True)
        bpy.data.cameras.remove(camera_data)
        bpy.data.objects.remove(light, do_unlink=True)
        bpy.data.lights.remove(light_data)


def test_gallery_has_no_offset_curve_shadows_on_cycles_gpu(tmp_path):
    try:
        enable_gpu_devices()
    except RuntimeError as error:
        pytest.skip(str(error))
    path = tmp_path / "gallery.png"
    subprocess.run(
        [sys.executable, "-m", "tests.visual_tests.test_curve_profiles", str(path)],
        check=True,
    )
    image = bpy.data.images.load(str(path), check_existing=False)
    try:
        pixels = image.pixels
        # These points lie just outside the blue curve and a purple dash.
        for x, y in ((600, 565), (714, 193)):
            offset = 4 * (y * 1200 + x)
            background = 4 * (y * 1200 + 1100)
            assert tuple(pixels[offset : offset + 3]) == pytest.approx(
                tuple(pixels[background : background + 3]), abs=0.06
            )
    finally:
        bpy.data.images.remove(image)
