"""Tests for reusable material color helpers."""

import bpy
import pytest
from mathutils import Color

import anima.materials.material as material_module
from anima.materials.material import (
    create_area_light,
    create_color_material,
    get_material_color,
    get_palette_color,
    hex_to_rgb,
    hex_to_rgb8,
    list_palettes,
    rgb8_to_hex,
    rgb8_to_rgb,
    rgb_to_hex,
    rgb_to_rgb8,
    rgba8_to_rgba,
    rgba_to_rgba8,
    srgb_to_linear_rgba,
    to_rgba,
)


@pytest.fixture(autouse=True)
def cleanup_blender_materials_and_lights():
    yield
    for material in list(bpy.data.materials):
        if material.name.startswith("pytest_"):
            bpy.data.materials.remove(material, do_unlink=True)
    for light in list(bpy.data.lights):
        if light.name.startswith("pytest_"):
            bpy.data.lights.remove(light, do_unlink=True)


def test_palette_lookup_returns_named_color():
    assert get_palette_color("byrne_euclid", "red1") == pytest.approx((216 / 255, 66 / 255, 39 / 255))
    assert get_palette_color("rougeux_euclid", "yellow") == pytest.approx((255 / 255, 192 / 255, 1 / 255))


def test_palette_lookup_raises_for_missing_values():
    with pytest.raises(KeyError):
        get_palette_color("missing", "coral")

    with pytest.raises(KeyError):
        get_palette_color("byrne_euclid", "missing")

    material_module.PALETTES["pytest_palette"] = {"invalid": 123}
    with pytest.raises(TypeError):
        get_palette_color("pytest_palette", "invalid")


def test_list_palettes_exposes_named_groups():
    palettes = list_palettes()
    assert "byrne_euclid" in palettes
    assert "rougeux_euclid" in palettes
    assert palettes["byrne_euclid"]["paper"] == "#FEF3D7"


def test_to_rgba_still_normalizes_alpha():
    assert to_rgba((0.1, 0.2, 0.3)) == (0.1, 0.2, 0.3, 1.0)
    assert to_rgba((0.1, 0.2, 0.3, 0.4)) == (0.1, 0.2, 0.3, 0.4)

    with pytest.raises(TypeError):
        to_rgba((0.1, 0.2))
    with pytest.raises(TypeError):
        to_rgba(("0.1", "0.2", "0.3"))


def test_srgb_to_linear_rgba_preserves_alpha():
    expected = (*Color((0.5, 0.0, 1.0)).from_srgb_to_scene_linear(), 0.25)
    assert srgb_to_linear_rgba((0.5, 0.0, 1.0, 0.25)) == pytest.approx(expected)

    with pytest.raises(TypeError):
        srgb_to_linear_rgba((0.5, 0.0))


def test_hex_and_rgb_conversion_roundtrip_and_validation():
    assert hex_to_rgb("#FF00AA") == pytest.approx((1.0, 0.0, 170 / 255))
    assert hex_to_rgb("FF00AA") == pytest.approx((1.0, 0.0, 170 / 255))
    assert rgb_to_hex((1.0, 0.0, 170 / 255)) == "#FF00AA"
    assert rgb_to_rgb8((1.0, 0.0, 170 / 255)) == (255, 0, 170)
    assert rgba_to_rgba8((1.0, 0.0, 170 / 255, 0.5)) == (255, 0, 170, 128)
    assert rgb8_to_rgb((255, 0, 170)) == pytest.approx((1.0, 0.0, 170 / 255))
    assert rgba8_to_rgba((255, 0, 170, 128)) == pytest.approx((1.0, 0.0, 170 / 255, 128 / 255))
    assert hex_to_rgb8("#FF00AA") == (255, 0, 170)
    assert rgb8_to_hex((255, 0, 170)) == "#FF00AA"

    with pytest.raises(TypeError):
        hex_to_rgb(123)
    with pytest.raises(ValueError):
        hex_to_rgb("#12345")
    with pytest.raises(ValueError):
        rgb_to_hex((256, 0, 0))
    with pytest.raises(ValueError):
        rgb_to_hex((1.0, 0.0))


def test_create_color_material_sets_blender_material_and_node_value():
    material_name = "pytest_material_node"
    material = create_color_material(material_name, (0.25, 0.5, 0.75, 0.8))

    assert material.name == material_name
    assert get_material_color(material) == pytest.approx((0.25, 0.5, 0.75, 0.8))
    assert material.use_nodes is True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    assert bsdf is not None
    assert tuple(bsdf.inputs["Base Color"].default_value) == pytest.approx((0.25, 0.5, 0.75, 0.8))

    legacy_name = "pytest_material_legacy"
    legacy_material = bpy.data.materials.new(legacy_name)
    legacy_material.use_nodes = False
    recreated = create_color_material(legacy_name, (0.1, 0.2, 0.3))
    assert recreated is legacy_material
    assert get_material_color(recreated) == pytest.approx((0.1, 0.2, 0.3, 1.0))


def test_create_area_light_sets_defaults():
    light = create_area_light("pytest_light")

    assert light.name == "pytest_light"
    assert light.data.type == "AREA"
    assert light.data.energy == 500
    assert light.data.shape == "DISK"
    assert light.data.size == 5
    assert tuple(light.location) == pytest.approx((0.0, 0.0, 5.0))

    default_light = create_area_light()
    assert default_light.name == "Key Light"
    assert default_light.data.type == "AREA"
