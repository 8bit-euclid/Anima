"""Verify that the default demo builders inherit the active background texture."""

from datetime import timedelta
from unittest.mock import MagicMock

import bpy
import pytest
from tests.utils.test_utils import create_rect_path
from tests.visual_tests import test_curves as curve_demo, test_latex as latex_demo, test_reveals as reveal_demo

from anima.animation.scheduler import Scheduler
from anima.materials.material import get_palette_color
from anima.materials.texture import NODE_PREFIX
from anima.primitives.curves import DEFAULT_LINE_WIDTH, THIN_LINE_WIDTH
from anima.primitives.object import Object
from anima.primitives.points import DEFAULT_POINT_RADIUS
from anima.scene.background import create_background
from anima.scene.state import clear_backgrounds


@pytest.fixture
def textured_demo(tmp_path, monkeypatch):
    old_objects = set(bpy.data.objects)
    old_materials = set(bpy.data.materials)
    image = bpy.data.images.new("pytest_demo_source", 4, 4)
    image.filepath_raw = str(tmp_path / "demo_Albedo.png")
    image.file_format = "PNG"
    image.save()
    bpy.data.images.remove(image)
    background = create_background(tmp_path)
    processor = MagicMock()
    processor.return_value.__enter__.return_value = (
        {"glyph": create_rect_path()},
        [("glyph", (0, 0), "A", None)],
    )
    monkeypatch.setattr("anima.latex.glyph_group.TeXDocumentProcessor", processor)
    inherited = []
    original = Object.inherit_textures_from

    def capture(target, source, **options):
        inherited.append((target, source))
        return original(target, source, **options)

    monkeypatch.setattr(Object, "inherit_textures_from", capture)
    Scheduler().reset()
    yield background, inherited
    Scheduler().reset()
    clear_backgrounds()
    for obj in set(bpy.data.objects) - old_objects:
        bpy.data.objects.remove(obj, do_unlink=True)
    for mat in set(bpy.data.materials) - old_materials:
        bpy.data.materials.remove(mat)
    loaded_image = bpy.data.images.get("demo_Albedo.png")
    if loaded_image is not None:
        bpy.data.images.remove(loaded_image)


def test_default_width_and_dependent_point_size():
    assert DEFAULT_LINE_WIDTH == pytest.approx(0.015)
    assert DEFAULT_POINT_RADIUS == pytest.approx(1.1 * DEFAULT_LINE_WIDTH)


def test_latex_and_reveals_inherit_textures_and_preserve_colors(textured_demo):
    background, inherited = textured_demo
    latex_demo.test_text_to_glyphs()
    reveal_demo.test_latex_write_on(timedelta(seconds=2))
    reveal_demo.test_curves_reveal(timedelta(seconds=2))

    assert len(inherited) == 7
    assert all(source is background for _, source in inherited)
    gallery = [target for target, _ in inherited[:5]]
    colors = ("black", "red1", "blue1", "yellow1", "black")
    for group, color in zip(gallery, colors):
        glyph = group[0]
        assert glyph.body.color[:3] == pytest.approx(get_palette_color("byrne_euclid", color))
        assert glyph.body.object.data.materials[0].node_tree.nodes.get(NODE_PREFIX + "albedo") is not None
        for curve in glyph.border.curves:
            assert curve.width == pytest.approx(THIN_LINE_WIDTH)
            assert curve.object.data.materials[0].node_tree.nodes.get(NODE_PREFIX + "albedo") is not None

    write_on, bars = [target for target, _ in inherited[5:]]
    assert write_on[0].body.color[:3] == pytest.approx(get_palette_color("byrne_euclid", "red1"))
    assert bars.children[0].object.data.materials[0].node_tree.nodes.get(NODE_PREFIX + "albedo") is not None
    assert bars.children[0].width == pytest.approx(0.1)


def test_curve_builders_use_registered_background(textured_demo):
    background, inherited = textured_demo
    duration = timedelta(seconds=2)
    curve_demo.test_bezier_splines(duration, color="red1")
    curve_demo.test_curve_joints(duration, color="yellow1")
    curve_demo.test_dashed_curves(duration, color="blue1")
    assert len(inherited) == 3
    assert all(source is background for _, source in inherited)
