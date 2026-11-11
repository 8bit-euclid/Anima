"""Tests for PBR texture sets and their application to materials."""

import importlib
from types import SimpleNamespace

import bpy
import pytest

import anima.materials.texture as texture_module
from anima.materials.texture import (
    NODE_PREFIX,
    TEXTURE_GROUP_NODE,
    TextureSet,
    _mean_ao,
    _mean_luminance,
    apply_texture_set,
    remove_texture_nodes,
)
from anima.primitives.lines import Segment
from anima.primitives.polytopes import Rectangle

MAPS = ("Albedo", "Roughness", "Normal", "Displacement", "AO")


@pytest.fixture
def texture_dir(tmp_path):
    for name in MAPS:
        img = bpy.data.images.new(f"pytest_{name}", 4, 4)
        img.filepath_raw = str(tmp_path / f"abc_4K_{name}.png")
        img.file_format = "PNG"
        img.save()
        bpy.data.images.remove(img)
    return tmp_path


@pytest.fixture(autouse=True)
def cleanup():
    existing_groups = set(bpy.data.node_groups)
    yield
    for obj in list(bpy.data.objects):
        if obj.name.startswith("pytest_"):
            bpy.data.objects.remove(obj, do_unlink=True)
    for material in list(bpy.data.materials):
        if material.name.startswith("pytest_"):
            bpy.data.materials.remove(material, do_unlink=True)
    for group in set(bpy.data.node_groups) - existing_groups:
        if group.users == 0:
            bpy.data.node_groups.remove(group)
    for image in list(bpy.data.images):
        if image.name.startswith("abc_"):
            bpy.data.images.remove(image)


def _linked_from(mat, socket):
    links = mat.node_tree.nodes["Principled BSDF"].inputs[socket].links
    return links[0].from_node if links else None


def _texture_group(mat):
    return mat.node_tree.nodes[TEXTURE_GROUP_NODE]


def _group_linked_from(group, socket):
    links = group.node_tree.nodes["Group Output"].inputs[socket].links
    return links[0].from_node if links else None


def test_from_directory_detects_maps(texture_dir):
    textures = TextureSet.from_directory(texture_dir, physical_size=2.5)
    assert set(textures.maps()) == {"albedo", "roughness", "normal", "height", "ao"}
    assert textures.physical_size == (2.5, 2.5)


def test_from_directory_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        TextureSet.from_directory(tmp_path / "nope")


def test_load_image_only_changes_colorspace_when_needed(tmp_path, monkeypatch):
    class ColorSpace:
        def __init__(self):
            self.value = "sRGB"
            self.assignments = []

        @property
        def name(self):
            return self.value

        @name.setter
        def name(self, value):
            self.assignments.append(value)
            self.value = value

    class Images:
        def __init__(self, image):
            self.image = image
            self.calls = []

        def load(self, path, *, check_existing):
            self.calls.append((path, check_existing))
            return self.image

    path = tmp_path / "texture.png"
    path.touch()
    colorspace = ColorSpace()
    image = SimpleNamespace(colorspace_settings=colorspace)
    images = Images(image)
    monkeypatch.setattr(texture_module, "bpy", SimpleNamespace(data=SimpleNamespace(images=images)))

    assert texture_module._load_image(path, "sRGB") is image
    assert texture_module._load_image(path, "Non-Color") is image
    assert texture_module._load_image(path, "Non-Color") is image
    assert texture_module._load_image(path, "sRGB") is image
    assert colorspace.assignments == ["Non-Color", "sRGB"]
    assert images.calls == [(str(path), True)] * 4
    path.unlink()
    with pytest.raises(FileNotFoundError, match="Texture map not found"):
        texture_module._load_image(path, "sRGB")


def test_replace_links_all_maps_with_correct_colorspaces(texture_dir):
    rect = Rectangle(2, 1, name="pytest_paper")
    rect.set_textures(TextureSet.from_directory(texture_dir), albedo_mode="replace")
    mat = rect.object.data.materials[0]
    group = _texture_group(mat)
    assert _linked_from(mat, "Roughness") == group
    assert _group_linked_from(group, "Roughness").image.colorspace_settings.name == "Non-Color"
    assert _group_linked_from(group, "Normal").type == "BUMP"
    assert _group_linked_from(group, "Base Color").type == "MIX"  # AO multiply
    albedo = group.node_tree.nodes[NODE_PREFIX + "albedo"]
    assert albedo.image.colorspace_settings.name == "sRGB"


def test_multiply_keeps_native_color_and_follows_updates(texture_dir):
    paper = Rectangle(2, 1, name="pytest_paper")
    paper.set_textures(TextureSet.from_directory(texture_dir))
    line = Segment((0, 0), (1, 0), name="pytest_line")
    line.set_color((1.0, 0.0, 0.0, 1.0))
    line.inherit_textures_from(paper)
    mat = line.object.data.materials[0]

    native = _texture_group(mat).inputs["Native Color"]
    assert tuple(native.default_value) == pytest.approx((1.0, 0.0, 0.0, 1.0))
    assert _linked_from(mat, "Roughness") is not None
    line.set_color((0.0, 0.0, 1.0, 1.0))
    assert tuple(native.default_value) == pytest.approx((0.0, 0.0, 1.0, 1.0))


def test_ignore_leaves_base_color_unlinked(texture_dir):
    rect = Rectangle(2, 1, name="pytest_paper")
    rect.set_color((0.2, 0.4, 0.6, 1.0))
    rect.set_textures(TextureSet.from_directory(texture_dir), albedo_mode="ignore")
    mat = rect.object.data.materials[0]
    assert _linked_from(mat, "Base Color") is None
    assert _linked_from(mat, "Roughness") is not None


@pytest.fixture
def grey_albedo(tmp_path):
    img = bpy.data.images.new("pytest_grey", 4, 4)
    img.pixels = [0.5, 0.5, 0.5, 1.0] * 16
    img.filepath_raw = str(tmp_path / "grey_Albedo.png")
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)
    return tmp_path / "grey_Albedo.png"


def test_mean_luminance_is_linear(grey_albedo):
    # sRGB 0.5 decodes to about 0.214 in linear light.
    assert _mean_luminance(grey_albedo) == pytest.approx(0.214, rel=0.02)


def test_modulate_normalises_albedo_by_its_mean(grey_albedo):
    rect = Rectangle(2, 1, name="pytest_paper")
    rect.set_color((0.2, 0.4, 0.6, 1.0))
    textures = TextureSet(albedo=grey_albedo)
    rect.set_textures(textures, albedo_mode="modulate", mottling_strength=0.5, use_ao=True)
    mat = rect.object.data.materials[0]
    group = _texture_group(mat)
    tint = _group_linked_from(group, "Base Color")
    assert tint.name == NODE_PREFIX + "tint"
    assert tint.blend_type == "MULTIPLY"
    variation = tint.inputs["B"].links[0].from_node
    mean = _mean_luminance(grey_albedo)
    assert variation.inputs[1].default_value == pytest.approx(0.5 / mean)
    assert variation.inputs[2].default_value == pytest.approx(0.5)
    # A pixel equal to the mean leaves the native color unchanged: mean * (k / mean) + (1 - k) == 1.
    assert mean * variation.inputs[1].default_value + variation.inputs[2].default_value == pytest.approx(1.0)
    assert tint.inputs["A"].links[0].from_node.type == "GROUP_INPUT"


def test_modulate_normalises_ao_by_its_mean(grey_albedo, tmp_path):
    ao = bpy.data.images.new("pytest_ao", 4, 4)
    ao.colorspace_settings.name = "Non-Color"
    ao.pixels = [0.8, 0.8, 0.8, 1.0] * 16
    ao.filepath_raw = str(tmp_path / "grey_AO.png")
    ao.file_format = "PNG"
    ao.save()
    bpy.data.images.remove(ao)

    rect = Rectangle(2, 1, name="pytest_paper")
    textures = TextureSet(albedo=grey_albedo, ao=tmp_path / "grey_AO.png")
    rect.set_textures(textures, albedo_mode="modulate", ao_strength=0.5)
    mat = rect.object.data.materials[0]

    mean = _mean_ao(textures.ao)
    assert mean == pytest.approx(0.8, abs=0.01)
    group = _texture_group(mat)
    ao_mul = group.node_tree.nodes[NODE_PREFIX + "ao_multiply"]
    variation = ao_mul.inputs["B"].links[0].from_node
    assert variation.name == NODE_PREFIX + "ao_variation"
    assert variation.inputs[1].default_value == pytest.approx(0.5 / mean)
    assert mean * variation.inputs[1].default_value + variation.inputs[2].default_value == pytest.approx(1.0)
    assert _group_linked_from(group, "Base Color").name == NODE_PREFIX + "ao_multiply"


def test_shared_group_keeps_material_color_and_opacity_independent(texture_dir):
    textures = TextureSet.from_directory(texture_dir)
    a = Rectangle(1, 1, name="pytest_a")
    b = Rectangle(1, 1, name="pytest_b")
    a.set_color((1.0, 0.0, 0.0, 1.0))
    b.set_color((0.0, 0.0, 1.0, 1.0))
    a.set_textures(textures, albedo_mode="modulate")
    b.set_textures(textures, albedo_mode="modulate")
    mat_a, mat_b = a.object.data.materials[0], b.object.data.materials[0]
    group_a, group_b = _texture_group(mat_a), _texture_group(mat_b)
    assert group_a.node_tree == group_b.node_tree

    a.set_color((0.0, 1.0, 0.0, 1.0))
    a.set_opacity(0.25)
    assert tuple(group_a.inputs["Native Color"].default_value) == pytest.approx((0, 1, 0, 1))
    assert tuple(group_b.inputs["Native Color"].default_value) == pytest.approx((0, 0, 1, 1))
    assert mat_a.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value == pytest.approx(0.25)
    assert mat_b.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value == pytest.approx(1)
    remove_texture_nodes(mat_a)
    assert tuple(mat_a.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value) == pytest.approx(
        (0, 1, 0, 1)
    )
    assert _texture_group(mat_b).node_tree == group_b.node_tree


def test_group_reused_after_module_reload_and_options_change(texture_dir):
    textures = TextureSet.from_directory(texture_dir)
    a = Rectangle(1, 1, name="pytest_a")
    b = Rectangle(1, 1, name="pytest_b")
    a.set_textures(textures, albedo_mode="modulate", mottling_strength=0.5)
    group = _texture_group(a.object.data.materials[0]).node_tree
    importlib.reload(texture_module)
    b.set_textures(textures, albedo_mode="modulate", mottling_strength=0.5)
    assert _texture_group(b.object.data.materials[0]).node_tree == group
    b.set_textures(textures, albedo_mode="modulate", mottling_strength=0.8)
    assert _texture_group(b.object.data.materials[0]).node_tree != group
    textures.physical_size = (2, 2)
    b.set_textures(textures, albedo_mode="modulate", mottling_strength=0.5)
    assert _texture_group(b.object.data.materials[0]).node_tree != group


def test_missing_map_is_reported_when_group_already_exists(grey_albedo):
    textures = TextureSet(albedo=grey_albedo)
    a = Rectangle(1, 1, name="pytest_a")
    a.set_textures(textures)
    grey_albedo.unlink()
    with pytest.raises(FileNotFoundError, match="Texture map not found"):
        a.set_textures(textures)
    assert _texture_group(a.object.data.materials[0]).node_tree is not None


def test_reuse_restores_deleted_image_datablock(grey_albedo):
    textures = TextureSet(albedo=grey_albedo)
    a = Rectangle(1, 1, name="pytest_a")
    b = Rectangle(1, 1, name="pytest_b")
    a.set_textures(textures)
    group = _texture_group(a.object.data.materials[0]).node_tree
    node = group.nodes[NODE_PREFIX + "albedo"]
    bpy.data.images.remove(node.image, do_unlink=True)
    assert node.image is None
    b.set_textures(textures)
    assert _texture_group(b.object.data.materials[0]).node_tree == group
    assert node.image is not None


def test_group_outputs_follow_selected_maps_and_options(texture_dir):
    textures = TextureSet.from_directory(texture_dir)
    textures.transmission = textures.roughness
    rect = Rectangle(1, 1, name="pytest_a")
    rect.set_textures(textures, albedo_mode="ignore", use_transmission=True)
    mat = rect.object.data.materials[0]
    group = _texture_group(mat)
    assert {output.name for output in group.outputs} == {"Roughness", "Transmission Weight", "Normal"}
    assert _linked_from(mat, "Base Color") is None
    assert _linked_from(mat, "Transmission Weight") == group
    assert _group_linked_from(group, "Transmission Weight").name == NODE_PREFIX + "transmission"
    rect.set_textures(TextureSet(ao=textures.ao), albedo_mode="modulate")
    group = _texture_group(mat)
    assert {output.name for output in group.outputs} == {"Base Color"}
    assert _group_linked_from(group, "Base Color").name == NODE_PREFIX + "ao_multiply"
    assert _linked_from(mat, "Normal") is None
    assert _linked_from(mat, "Transmission Weight") is None


@pytest.mark.parametrize("mode", ["replace", "ignore"])
def test_removing_group_preserves_unrelated_base_color(mode, grey_albedo):
    rect = Rectangle(1, 1, name="pytest_a")
    rect.set_color((0.2, 0.4, 0.6, 1.0))
    mat = rect.object.data.materials[0]
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    custom_color = (0.7, 0.6, 0.5, 1.0)
    bsdf.inputs["Base Color"].default_value = custom_color
    apply_texture_set(mat, TextureSet(albedo=grey_albedo), albedo_mode=mode)
    remove_texture_nodes(mat)
    assert tuple(bsdf.inputs["Base Color"].default_value) == pytest.approx(custom_color)


def test_inherit_defaults_to_modulate(texture_dir):
    paper = Rectangle(2, 1, name="pytest_paper")
    paper.set_textures(TextureSet.from_directory(texture_dir))
    rect = Rectangle(1, 1, name="pytest_a")
    rect.inherit_textures_from(paper)
    assert rect._texture_options["albedo_mode"] == "modulate"


def test_reapply_and_remove_are_clean(texture_dir):
    rect = Rectangle(2, 1, name="pytest_paper")
    textures = TextureSet.from_directory(texture_dir)
    rect.set_textures(textures)
    mat = rect.object.data.materials[0]
    count = len(mat.node_tree.nodes)
    apply_texture_set(mat, textures)
    assert len(mat.node_tree.nodes) == count
    remove_texture_nodes(mat)
    assert not any(n.name.startswith(NODE_PREFIX) for n in mat.node_tree.nodes)
    assert _linked_from(mat, "Roughness") is None


def test_inherit_without_textures_raises():
    a = Rectangle(1, 1, name="pytest_a")
    b = Rectangle(1, 1, name="pytest_b")
    with pytest.raises(ValueError):
        b.inherit_textures_from(a)


def test_group_forwards_material_and_textures_without_data(texture_dir):
    from anima.primitives.group import Group

    a = Rectangle(1, 1, name="pytest_a")
    b = Rectangle(1, 1, name="pytest_b")
    paper = Rectangle(2, 1, name="pytest_paper")
    paper.set_textures(TextureSet.from_directory(texture_dir))
    group = Group([a, b], name="pytest_group")
    assert group.object.data is None

    group.set_color((0.0, 1.0, 0.0, 1.0))
    group.inherit_textures_from(paper, albedo_mode="ignore")
    for rect in (a, b):
        mat = rect.object.data.materials[0]
        assert tuple(mat.diffuse_color) == pytest.approx((0.0, 1.0, 0.0, 1.0))
        assert _linked_from(mat, "Roughness") is not None
        assert _linked_from(mat, "Base Color") is None
    assert not group.object.parent
    assert a.object.parent is group.object
