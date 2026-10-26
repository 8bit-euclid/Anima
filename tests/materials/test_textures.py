"""Tests for PBR texture sets and their application to materials."""

import bpy
import pytest

from anima.materials.texture import (
    NODE_PREFIX,
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
    yield
    for obj in list(bpy.data.objects):
        if obj.name.startswith("pytest_"):
            bpy.data.objects.remove(obj, do_unlink=True)
    for material in list(bpy.data.materials):
        if material.name.startswith("pytest_"):
            bpy.data.materials.remove(material, do_unlink=True)
    for image in list(bpy.data.images):
        if image.name.startswith("abc_"):
            bpy.data.images.remove(image)


def _linked_from(mat, socket):
    links = mat.node_tree.nodes["Principled BSDF"].inputs[socket].links
    return links[0].from_node if links else None


def test_from_directory_detects_maps(texture_dir):
    textures = TextureSet.from_directory(texture_dir, physical_size=2.5)
    assert set(textures.maps()) == {"albedo", "roughness", "normal", "height", "ao"}
    assert textures.physical_size == (2.5, 2.5)


def test_from_directory_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        TextureSet.from_directory(tmp_path / "nope")


def test_replace_links_all_maps_with_correct_colorspaces(texture_dir):
    rect = Rectangle(2, 1, name="pytest_paper")
    rect.set_textures(TextureSet.from_directory(texture_dir), albedo_mode="replace")
    mat = rect.object.data.materials[0]
    assert _linked_from(mat, "Roughness").image.colorspace_settings.name == "Non-Color"
    assert _linked_from(mat, "Normal").type == "BUMP"
    assert _linked_from(mat, "Base Color").type == "MIX"  # AO multiply
    albedo = mat.node_tree.nodes[NODE_PREFIX + "albedo"]
    assert albedo.image.colorspace_settings.name == "sRGB"


def test_multiply_keeps_native_color_and_follows_updates(texture_dir):
    paper = Rectangle(2, 1, name="pytest_paper")
    paper.set_textures(TextureSet.from_directory(texture_dir))
    line = Segment((0, 0), (1, 0), name="pytest_line")
    line.set_color((1.0, 0.0, 0.0, 1.0))
    line.inherit_textures_from(paper)
    mat = line.object.data.materials[0]

    native = mat.node_tree.nodes[NODE_PREFIX + "native_color"]
    assert tuple(native.outputs[0].default_value) == pytest.approx((1.0, 0.0, 0.0, 1.0))
    assert _linked_from(mat, "Roughness") is not None
    line.set_color((0.0, 0.0, 1.0, 1.0))
    assert tuple(native.outputs[0].default_value) == pytest.approx((0.0, 0.0, 1.0, 1.0))


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
    tint = _linked_from(mat, "Base Color")
    assert tint.name == NODE_PREFIX + "tint"
    assert tint.blend_type == "MULTIPLY"
    variation = tint.inputs["B"].links[0].from_node
    mean = _mean_luminance(grey_albedo)
    assert variation.inputs[1].default_value == pytest.approx(0.5 / mean)
    assert variation.inputs[2].default_value == pytest.approx(0.5)
    # A pixel equal to the mean leaves the native color unchanged: mean * (k / mean) + (1 - k) == 1.
    assert mean * variation.inputs[1].default_value + variation.inputs[2].default_value == pytest.approx(1.0)
    assert tint.inputs["A"].links[0].from_node.name == NODE_PREFIX + "native_color"


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
    ao_mul = mat.node_tree.nodes[NODE_PREFIX + "ao_multiply"]
    variation = ao_mul.inputs["B"].links[0].from_node
    assert variation.name == NODE_PREFIX + "ao_variation"
    assert variation.inputs[1].default_value == pytest.approx(0.5 / mean)
    assert mean * variation.inputs[1].default_value + variation.inputs[2].default_value == pytest.approx(1.0)
    assert _linked_from(mat, "Base Color").name == NODE_PREFIX + "ao_multiply"


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
