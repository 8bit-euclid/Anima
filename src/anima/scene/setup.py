"""Set up profile lighting and an orthographic starting camera."""

import bpy

from anima.scene.state import get_profile
from anima.utils.render import ensure_camera


def configure_camera() -> bpy.types.Object:
    """Configure the active camera for the profile's centered, top-down view.

    The render resolution must match the profile; pixel aspect is set to square,
    render borders and depth of field are disabled. The camera remains editable
    afterwards, including for intentional zooms.
    """
    profile = get_profile()
    scene = bpy.context.scene
    profile.validate_resolution((scene.render.resolution_x, scene.render.resolution_y))
    camera = ensure_camera()
    if camera.parent is not None or camera.constraints:
        raise ValueError("The profile camera must not have a parent or constraints.")
    if camera.animation_data is not None or camera.data.animation_data is not None:
        raise ValueError("The profile camera must not already have animation or drivers.")
    scene.render.resolution_percentage = 100
    scene.render.pixel_aspect_x = scene.render.pixel_aspect_y = 1
    scene.render.use_border = False
    camera.location = (0, 0, profile.camera_height)
    camera.rotation_mode = "XYZ"
    camera.rotation_euler = (0, 0, 0)
    camera.scale = (1, 1, 1)
    camera.delta_location = (0, 0, 0)
    camera.delta_rotation_euler = (0, 0, 0)
    camera.delta_scale = (1, 1, 1)
    camera.data.type = "ORTHO"
    camera.data.dof.use_dof = False
    camera.data.ortho_scale = max(profile.frame_width, profile.frame_height)
    camera.data.shift_x = camera.data.shift_y = 0
    camera.data.clip_start = profile.clip_start
    camera.data.clip_end = profile.clip_end
    return camera


def configure_lighting() -> bpy.types.Object:
    """Set up fixed lighting and color management for the profile.

    Returns:
        The fixed raking sun. The new world belongs to the active scene.
    """
    profile = get_profile()
    scene = bpy.context.scene
    world = bpy.data.worlds.new("Scene World")
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.05, 0.05, 0.05, 1)
    background.inputs["Strength"].default_value = 1
    scene.world = world
    scene.render.film_transparent = False
    scene.display_settings.display_device = "sRGB"
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1
    light = bpy.data.objects.new("Scene Sun", bpy.data.lights.new("Scene Sun", "SUN"))
    bpy.context.collection.objects.link(light)
    light.rotation_euler = profile.sun_rotation
    light.data.energy = profile.sun_energy
    return light
