"""Tests for PBR texture sets and their application to materials."""

import importlib
from types import SimpleNamespace

import bpy
import pytest

import anima.materials.texture as texture_module
from anima.animation.effects import Fade
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


def test_recursive_texture_application_prepares_maps_once_per_root(texture_dir, monkeypatch):
    from anima.primitives.group import Group

    textures = TextureSet.from_directory(texture_dir)
    roots = [
        Group([Rectangle(1, 1, name=f"pytest_{root}_{child}") for child in range(2)], name=f"pytest_root_{root}")
        for root in range(2)
    ]
    calls = 0
    original_maps = TextureSet.maps

    def count_maps(self):
        nonlocal calls
        calls += 1
        return original_maps(self)

    monkeypatch.setattr(TextureSet, "maps", count_maps)

    roots[0].set_textures(textures, albedo_mode="modulate", mottling_strength=0.5)
    assert calls == 1
    roots[1].set_textures(textures, albedo_mode="modulate", mottling_strength=0.5)
    assert calls == 2

    roots[0].set_textures(textures, albedo_mode="modulate", mottling_strength=0.8)
    assert calls == 3
    assert (
        _texture_group(roots[0].children[0].object.data.materials[0]).node_tree
        != _texture_group(roots[1].children[0].object.data.materials[0]).node_tree
    )


def test_copy_textured_material_keeps_per_material_state_independent(texture_dir):
    textures = TextureSet.from_directory(texture_dir)
    original = Rectangle(1, 1, name="pytest_textured_copy")
    original.set_color((1.0, 0.0, 0.0, 1.0))
    original.set_textures(textures, albedo_mode="modulate")
    copied = original.copy()
    source_mat = original.object.data.materials[0]
    copy_mat = copied.object.data.materials[0]
    source_group = _texture_group(source_mat)
    copy_group = _texture_group(copy_mat)
    assert copy_mat != source_mat
    assert copy_mat.node_tree != source_mat.node_tree
    assert source_group.node_tree == copy_group.node_tree

    copied.set_color((0.0, 0.0, 1.0, 1.0))
    copied.set_opacity(0.25)
    assert tuple(source_group.inputs["Native Color"].default_value) == pytest.approx((1, 0, 0, 1))
    assert tuple(copy_group.inputs["Native Color"].default_value) == pytest.approx((0, 0, 1, 1))
    assert original.opacity == pytest.approx(1)
    copied.set_textures(textures, albedo_mode="ignore")
    assert _texture_group(source_mat).node_tree == source_group.node_tree
    assert _texture_group(copy_mat).node_tree != source_group.node_tree
    original.set_color((0.0, 1.0, 0.0, 1.0))
    assert copied.color == pytest.approx((0, 0, 1, 0.25))


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


@pytest.fixture
def height_map(tmp_path):
    image = bpy.data.images.new("pytest_height", 4, 1)
    image.colorspace_settings.name = "Non-Color"
    image.pixels = [channel for value in (0.0, 0.25, 0.75, 1.0) for channel in (value, value, value, 1.0)]
    image.filepath_raw = str(tmp_path / "height.png")
    image.file_format = "PNG"
    image.save()
    bpy.data.images.remove(image)
    path = tmp_path / "height.png"
    yield path
    for loaded in list(bpy.data.images):
        if bpy.path.abspath(loaded.filepath) == str(path):
            bpy.data.images.remove(loaded, do_unlink=True)
    texture_module._height_samples.cache_clear()


def test_height_percentiles_use_map_distribution_and_cache(height_map):
    texture_module._height_samples.cache_clear()
    low, high = texture_module._height_thresholds(height_map, (0.25, 0.75))
    assert (low, high) == pytest.approx((0.1875, 0.8125), abs=0.002)
    assert texture_module._height_thresholds(height_map, (0.0, 1.0)) == pytest.approx((0, 1))
    assert texture_module._height_samples.cache_info().hits == 1


def test_height_percentiles_refresh_when_file_changes(height_map):
    rect = Rectangle(1, 1, name="pytest_reveal_refresh")
    textures = TextureSet(height=height_map)
    rect.set_textures(textures, height_reveal=(0.0, 1.0))
    old_group = _texture_group(rect.object.data.materials[0]).node_tree
    image = bpy.data.images.new("pytest_height_replacement", 4, 1)
    image.colorspace_settings.name = "Non-Color"
    image.pixels = [channel for value in (0.25, 0.4, 0.6, 0.75) for channel in (value, value, value, 1.0)]
    image.filepath_raw = str(height_map)
    image.file_format = "PNG"
    image.save()
    bpy.data.images.remove(image)

    rect.set_textures(textures, height_reveal=(0.0, 1.0))
    group = _texture_group(rect.object.data.materials[0]).node_tree
    assert group != old_group
    coverage = group.nodes[NODE_PREFIX + "reveal_coverage"]
    assert coverage.inputs["From Min"].default_value == pytest.approx(0.25, abs=0.005)
    assert coverage.inputs["From Max"].default_value == pytest.approx(0.75, abs=0.005)


def test_height_reveal_rejects_unsaved_pixel_edits(height_map):
    rect = Rectangle(1, 1, name="pytest_reveal_dirty")
    textures = TextureSet(height=height_map)
    rect.set_textures(textures, height_reveal=(0.25, 0.75))
    group = _texture_group(rect.object.data.materials[0])
    image = group.node_tree.nodes[NODE_PREFIX + "height"].image
    image.pixels[0] = 0.5
    assert image.is_dirty
    with pytest.raises(ValueError, match="Save or reload"):
        rect.set_textures(textures, height_reveal=(0.25, 0.75))
    assert _texture_group(rect.object.data.materials[0]) == group


@pytest.mark.parametrize(
    ("percentiles", "coverage"),
    [
        ((-0.1, 0.5), (0.0, 1.0)),
        ((0.8, 0.2), (0.0, 1.0)),
        ((0.0, float("nan")), (0.0, 1.0)),
        ((0.0, 1.0), (0.0, 1.1)),
        ((0.0, 1.0), (float("inf"), 1.0)),
    ],
)
def test_invalid_height_reveal_options_raise(height_map, percentiles, coverage):
    rect = Rectangle(1, 1, name="pytest_reveal_invalid")
    with pytest.raises(ValueError):
        rect.set_textures(TextureSet(height=height_map), height_reveal=percentiles, ink_coverage=coverage)


def test_height_reveal_requires_height_and_rejects_collapsed_gradient(grey_albedo):
    rect = Rectangle(1, 1, name="pytest_reveal_invalid")
    with pytest.raises(ValueError, match="requires a height map"):
        rect.set_textures(TextureSet(albedo=grey_albedo), height_reveal=(0.2, 0.8))
    with pytest.raises(ValueError, match="same height"):
        rect.set_textures(TextureSet(height=grey_albedo), height_reveal=(0.2, 0.8))
    rect.set_textures(TextureSet(height=grey_albedo), height_reveal=(0.5, 0.5))


def test_failed_height_reveal_preserves_inheritable_texture_options(height_map, grey_albedo):
    rect = Rectangle(1, 1, name="pytest_reveal_source")
    original = TextureSet(height=height_map)
    rect.set_textures(original, height_reveal=(0.25, 0.75))
    with pytest.raises(ValueError, match="requires a height map"):
        rect.set_textures(TextureSet(albedo=grey_albedo), height_reveal=(0.25, 0.75))
    target = Rectangle(1, 1, name="pytest_reveal_target")
    target.inherit_textures_from(rect)
    assert target._texture_set is original
    assert target._texture_options["height_reveal"] == (0.25, 0.75)


def test_height_reveal_does_not_replace_custom_alpha_link(height_map):
    rect = Rectangle(1, 1, name="pytest_reveal_custom_alpha")
    rect.set_opacity(0.7)
    mat = rect.object.data.materials[0]
    tree = mat.node_tree
    custom = tree.nodes.new("ShaderNodeValue")
    alpha = tree.nodes["Principled BSDF"].inputs["Alpha"]
    tree.links.new(custom.outputs[0], alpha)
    with pytest.raises(ValueError, match="custom Alpha"):
        rect.set_textures(TextureSet(height=height_map), height_reveal=(0.25, 0.75))
    assert alpha.links[0].from_node == custom


def test_height_reveal_preserves_independent_opacity_and_fades(height_map):
    textures = TextureSet(height=height_map)
    a = Rectangle(1, 1, name="pytest_reveal_a")
    b = Rectangle(1, 1, name="pytest_reveal_b")
    a.set_color((0.0, 0.0, 0.0, 0.7))
    b.set_opacity(0.9)
    a.set_textures(textures, height_reveal=(0.25, 0.75))
    b.set_textures(textures, height_reveal=(0.25, 0.75))
    mat_a, mat_b = a.object.data.materials[0], b.object.data.materials[0]
    group_a, group_b = _texture_group(mat_a), _texture_group(mat_b)
    assert group_a.node_tree == group_b.node_tree
    assert group_a.inputs["Native Opacity"].default_value == pytest.approx(0.7)
    assert group_b.inputs["Native Opacity"].default_value == pytest.approx(0.9)
    assert _linked_from(mat_a, "Alpha") == group_a

    Fade(a).apply(0.3)
    assert a.opacity == pytest.approx(0.3)
    assert group_a.inputs["Native Opacity"].default_value == pytest.approx(0.3)
    assert group_b.inputs["Native Opacity"].default_value == pytest.approx(0.9)
    a.set_color((0.2, 0.3, 0.4))
    assert a.color == pytest.approx((0.2, 0.3, 0.4, 0.3))
    a.set_textures(textures, height_reveal=(0.5, 0.5))
    assert _texture_group(mat_a).inputs["Native Opacity"].default_value == pytest.approx(0.3)
    remove_texture_nodes(mat_a)
    assert _linked_from(mat_a, "Alpha") is None
    assert a.opacity == pytest.approx(0.3)


@pytest.mark.parametrize(
    ("percentiles", "coverage", "relative_heights", "expected"),
    [
        ((0.25, 0.75), (0.2, 0.8), (-0.1, 0.0, 0.5, 1.0, 1.1), (0.2, 0.2, 0.5, 0.8, 0.8)),
        ((0.25, 0.75), (0.8, 0.2), (-0.1, 0.5, 1.1), (0.8, 0.5, 0.2)),
        ((0.5, 0.5), (0.2, 0.8), (-0.1, 0.0, 0.1), (0.2, 0.8, 0.8)),
    ],
)
def test_height_reveal_shader_output(height_map, tmp_path, percentiles, coverage, relative_heights, expected):
    rect = Rectangle(1, 1, name="pytest_reveal_shader")
    rect.set_opacity(0.5)
    rect.set_textures(TextureSet(height=height_map), height_reveal=percentiles, ink_coverage=coverage)
    mat = rect.object.data.materials[0]
    group = _texture_group(mat)
    nodes, links = group.node_tree.nodes, group.node_tree.links
    source = nodes.new("ShaderNodeValue")
    target = nodes.get(NODE_PREFIX + "reveal_below") or nodes[NODE_PREFIX + "reveal_coverage"]
    assert target.inputs[0].links[0].from_node == nodes[NODE_PREFIX + "height"]
    links.new(source.outputs[0], target.inputs[0])

    tree = mat.node_tree
    emission = tree.nodes.new("ShaderNodeEmission")
    tree.links.new(group.outputs["Alpha"], emission.inputs["Color"])
    tree.links.new(emission.outputs["Emission"], tree.nodes["Material Output"].inputs["Surface"])
    scene = bpy.data.scenes.new("pytest_reveal_render")
    camera_data = bpy.data.cameras.new("pytest_reveal_camera")
    camera = bpy.data.objects.new("pytest_reveal_camera", camera_data)
    scene.collection.objects.link(camera)
    scene.collection.objects.link(rect.object)
    camera.location = (0, 0, 5)
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 0.5
    scene.camera = camera
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 4
    scene.cycles.use_denoising = False
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 2
    scene.render.resolution_x = scene.render.resolution_y = 4
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.dither_intensity = 0
    scene.view_settings.view_transform = "Standard"
    low, high = texture_module._height_thresholds(height_map, percentiles)
    try:
        for index, (relative, desired) in enumerate(zip(relative_heights, expected)):
            source.outputs[0].default_value = low + relative * (high - low if high != low else 1)
            path = tmp_path / f"result_{index}.png"
            scene.render.filepath = str(path)
            bpy.ops.render.render(scene=scene.name, write_still=True)
            image = bpy.data.images.load(str(path))
            encoded = image.pixels[0]
            bpy.data.images.remove(image)
            linear = encoded / 12.92 if encoded <= 0.04045 else ((encoded + 0.055) / 1.055) ** 2.4
            assert linear == pytest.approx(desired * 0.5, abs=0.005)
    finally:
        bpy.data.scenes.remove(scene)
        bpy.data.objects.remove(camera, do_unlink=True)
        bpy.data.cameras.remove(camera_data)


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
