from dataclasses import replace
from types import SimpleNamespace

import bpy
import pytest

from anima.scene.background import create_background, get_background
from anima.scene.profile import FRAME_16X9_V1
from anima.scene.setup import configure_camera, configure_lighting
from anima.scene.state import clear_backgrounds


def test_default_profile_dimensions_and_pixel_density():
    profile = FRAME_16X9_V1
    assert profile.name == "paper-16x9-v1"
    assert profile.frame_height == pytest.approx(11.25)
    assert profile.background_size == pytest.approx((20.4, 11.65))
    assert profile.safe_size == pytest.approx((18, 10.125))
    assert profile.pixels_per_unit(profile.preview_resolution) == 96
    assert profile.pixels_per_unit(profile.master_resolution) == 192


@pytest.mark.parametrize("resolution", [(0, 0), (1920, 1200), (1920.0, 1080), (-16, -9)])
def test_profile_rejects_invalid_resolutions(resolution):
    with pytest.raises(ValueError, match="Resolution"):
        FRAME_16X9_V1.validate_resolution(resolution)


@pytest.mark.parametrize(
    "values",
    [
        {"frame_width": 0},
        {"safe_margin": 0.5},
        {"background_bleed": -1},
        {"body_font_size": float("nan")},
        {"label_font_size": 0},
        {"title_font_size": -1},
        {"tex_point_size": float("inf")},
        {"camera_height": 0.01},
        {"clip_end": 5},
        {"aspect_width": 0},
        {"preview_resolution": (1920, 1200)},
    ],
)
def test_profile_rejects_invalid_dimensions(values):
    with pytest.raises(ValueError):
        replace(FRAME_16X9_V1, **values)


def test_profile_camera_reconfigures_existing_camera_and_covers_paper_plane():
    scene = bpy.context.scene
    original_camera = scene.camera
    original_resolution = (scene.render.resolution_x, scene.render.resolution_y)
    original_percentage = scene.render.resolution_percentage
    original_border = scene.render.use_border
    original_aspect = (scene.render.pixel_aspect_x, scene.render.pixel_aspect_y)
    camera_data = bpy.data.cameras.new("pytest_camera")
    camera = bpy.data.objects.new("pytest_camera", camera_data)
    scene.collection.objects.link(camera)
    try:
        scene.camera = camera
        scene.render.resolution_x, scene.render.resolution_y = FRAME_16X9_V1.preview_resolution
        scene.render.pixel_aspect_x = 2
        scene.render.resolution_percentage = 50
        scene.render.use_border = True
        camera.data.dof.use_dof = True
        camera.location = (1, 2, 3)
        camera.rotation_euler = (1, 1, 1)
        camera.data.shift_x = 0.2
        configured = configure_camera()
        assert configured == camera
        assert camera.data.type == "ORTHO"
        assert tuple(camera.location) == pytest.approx((0, 0, 10))
        assert tuple(camera.rotation_euler) == pytest.approx((0, 0, 0))
        assert (scene.render.pixel_aspect_x, scene.render.pixel_aspect_y) == (1, 1)
        assert scene.render.resolution_percentage == 100
        assert not scene.render.use_border
        assert not camera.data.dof.use_dof
        corners = camera.data.view_frame(scene=scene)
        assert max(p.x for p in corners) - min(p.x for p in corners) == pytest.approx(20)
        assert max(p.y for p in corners) - min(p.y for p in corners) == pytest.approx(11.25)
        assert camera.data.shift_x == 0
        assert camera.data.clip_start < camera.location.z < camera.data.clip_end
        camera.data.ortho_scale = 10
        assert camera.data.ortho_scale == 10
    finally:
        scene.camera = original_camera
        scene.render.resolution_x, scene.render.resolution_y = original_resolution
        scene.render.resolution_percentage = original_percentage
        scene.render.use_border = original_border
        scene.render.pixel_aspect_x, scene.render.pixel_aspect_y = original_aspect
        bpy.data.objects.remove(camera, do_unlink=True)
        bpy.data.cameras.remove(camera_data)


@pytest.mark.parametrize("kind", ["parent", "constraint", "animation", "data_animation"])
def test_profile_camera_rejects_external_transforms(kind):
    scene = bpy.context.scene
    original_camera = scene.camera
    original_resolution = (scene.render.resolution_x, scene.render.resolution_y)
    camera_data = bpy.data.cameras.new("pytest_camera")
    camera = bpy.data.objects.new("pytest_camera", camera_data)
    parent = bpy.data.objects.new("pytest_parent", None)
    scene.collection.objects.link(camera)
    scene.collection.objects.link(parent)
    try:
        scene.camera = camera
        scene.render.resolution_x, scene.render.resolution_y = FRAME_16X9_V1.preview_resolution
        if kind == "parent":
            camera.parent = parent
        elif kind == "constraint":
            camera.constraints.new("COPY_LOCATION")
        elif kind == "animation":
            camera.animation_data_create()
        else:
            camera_data.animation_data_create()
        with pytest.raises(ValueError, match="profile camera"):
            configure_camera()
    finally:
        scene.camera = original_camera
        scene.render.resolution_x, scene.render.resolution_y = original_resolution
        bpy.data.objects.remove(camera, do_unlink=True)
        bpy.data.objects.remove(parent, do_unlink=True)
        bpy.data.cameras.remove(camera_data)


def test_scene_lighting_is_fixed():
    scene = bpy.context.scene
    original_world = scene.world
    original_transparency = scene.render.film_transparent
    original_display = scene.display_settings.display_device
    original_view = scene.view_settings.view_transform
    original_look = scene.view_settings.look
    original_exposure = scene.view_settings.exposure
    original_gamma = scene.view_settings.gamma
    light = configure_lighting()
    world = scene.world
    data = light.data
    try:
        assert data.type == "SUN"
        assert data.energy == 4
        assert tuple(light.rotation_euler) == pytest.approx(FRAME_16X9_V1.sun_rotation)
        assert light.animation_data is None
        assert world.node_tree.nodes["Background"].inputs["Color"].default_value[:] == pytest.approx(
            (0.05, 0.05, 0.05, 1)
        )
        assert scene.view_settings.view_transform == "AgX"
        assert scene.view_settings.look == "None"
        assert scene.view_settings.exposure == 0
    finally:
        scene.world = original_world
        scene.render.film_transparent = original_transparency
        scene.display_settings.display_device = original_display
        scene.view_settings.view_transform = original_view
        scene.view_settings.look = original_look
        scene.view_settings.exposure = original_exposure
        scene.view_settings.gamma = original_gamma
        bpy.data.objects.remove(light, do_unlink=True)
        bpy.data.lights.remove(data)
        bpy.data.worlds.remove(world)


def test_create_background_requires_recognized_texture_maps(tmp_path):
    clear_backgrounds()
    with pytest.raises(FileNotFoundError, match="No background texture maps"):
        create_background(tmp_path)
    with pytest.raises(RuntimeError, match="No active background"):
        get_background()


def test_create_background_has_bleed_and_profile_texture_size(tmp_path):
    image = bpy.data.images.new("pytest_source", 4, 4)
    image.filepath_raw = str(tmp_path / "paper_Albedo.png")
    image.file_format = "PNG"
    image.save()
    bpy.data.images.remove(image)
    paper = create_background(tmp_path)
    material = paper.object.data.materials[0]
    loaded_image = bpy.data.images.get("paper_Albedo.png")
    try:
        assert get_background() is paper
        vertices = [tuple(vertex.co) for vertex in paper.vertices]
        assert min(vertex[0] for vertex in vertices) == pytest.approx(-10.2)
        assert max(vertex[0] for vertex in vertices) == pytest.approx(10.2)
        assert min(vertex[1] for vertex in vertices) == pytest.approx(-5.825)
        assert max(vertex[1] for vertex in vertices) == pytest.approx(5.825)
        assert paper.layer == -1
        assert paper._texture_set.physical_size == (10, 10)
    finally:
        clear_backgrounds()
        bpy.data.objects.remove(paper.object, do_unlink=True)
        bpy.data.materials.remove(material)
        if loaded_image is not None:
            bpy.data.images.remove(loaded_image)


def test_background_rejects_deleted_object():
    from anima.primitives.polytopes import Rectangle
    from anima.scene.state import register_background

    background = Rectangle(1, 1, name="pytest_background")
    register_background(background)
    bpy.data.objects.remove(background.object, do_unlink=True)
    with pytest.raises(RuntimeError, match="No active background"):
        get_background()


def test_clear_scene_forgets_active_background(monkeypatch):
    import anima.globals.general as general
    from anima.primitives.polytopes import Rectangle
    from anima.scene.state import register_background

    background = Rectangle(1, 1, name="pytest_background")
    register_background(background)
    monkeypatch.setattr(general, "bpy", SimpleNamespace(data=SimpleNamespace(objects=[])))
    try:
        general.clear_scene()
        with pytest.raises(RuntimeError, match="No active background"):
            get_background()
    finally:
        bpy.data.objects.remove(background.object, do_unlink=True)


def test_background_registration_is_scoped_to_scene():
    from anima.primitives.polytopes import Rectangle
    from anima.scene.state import register_background

    window = bpy.context.window
    original_scene = window.scene
    other_scene = bpy.data.scenes.new("pytest_other_scene")
    background = Rectangle(1, 1, name="pytest_background")
    try:
        register_background(background)
        window.scene = other_scene
        with pytest.raises(RuntimeError, match="No active background"):
            get_background()
        window.scene = original_scene
        assert get_background() is background
    finally:
        window.scene = original_scene
        clear_backgrounds()
        bpy.data.objects.remove(background.object, do_unlink=True)
        bpy.data.scenes.remove(other_scene)
