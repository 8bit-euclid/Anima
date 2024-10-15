import bpy
from collections import namedtuple
from math import *
from mathutils import Vector, Matrix, Euler
from datetime import timedelta
from typing import List
from apeiron.easybpy import *


UnitZ = Vector([0.0, 0.0, 1.0])

Interval = namedtuple("Interval", ['start', 'stop'])


def assert_2d(dim):
    assert dim == 2, "Can only handle 2D, currently."


def clear_scene():
    for obj in bpy.data.objects:
        bpy.data.objects.remove(obj, do_unlink=True)


def create_mesh(name: str, verts, faces, edges=[]):
    mesh = bpy.data.meshes.new(name)  # Create a new mesh
    # Load vertices, edges, and faces to the mesh
    mesh.from_pydata(verts, edges, faces)
    mesh.update()
    return mesh


def link_object(obj):
    bpy.data.collections['Collection'].objects.link(obj)


def add_object(name: str, mesh):
    obj = bpy.data.objects.new(name, mesh)
    link_object(obj)
    return obj


def add_empty(name='Empty', location=(0, 0, 0)):
    bpy.ops.object.empty_add(name=name, location=location, type='PLAIN_AXES')
    return bpy.context.view_layer.objects.active


def add_empty_hook(name, parent, vertex_index):
    hook = add_hook(parent)
    hook.object = add_empty(name, parent.data.vertices[vertex_index].co)
    hook.object.parent = parent
    hook.object.hide_viewport = True
    hook.object.hide_render = True
    hook.vertex_indices_set([vertex_index])
    return hook


def add_rectangle(location=(0, 0, 0)):
    bpy.ops.mesh.primitive_plane_add(
        size=1, enter_editmode=False, align='WORLD', location=location)
    return bpy.context.view_layer.objects.active


def add_driver_script(driver, object, data_path, var_name, expression):
    driver.type = 'SCRIPTED'
    driver.expression = expression

    var = driver.variables.new()
    var.name = var_name
    var.targets[0].id_type = 'OBJECT'
    var.targets[0].id = object
    var.targets[0].data_path = data_path


def time(time_str: str) -> timedelta:
    """Accepts a time string of the form mm:ss or mm:ss:mmm and returns the corresponding timedelta object"""

    units = time_str.split(':')
    assert len(units) in [
        2, 3], "Accepted time formats are mm:ss and mm:ss:mmm"
    assert len(units[0]) == 2
    assert len(units[1]) == 2

    delta = timedelta(minutes=int(units[0]), seconds=int(units[1]))
    if len(units) == 3:
        assert len(units[2]) == 3
        delta += timedelta(milliseconds=int(units[2]))

    return delta


def to_frame(delta):
    if isinstance(delta, str):
        delta = time(delta)

    assert delta < timedelta(
        hours=1), "Can only convert up to 1hr to a frame index."
    return round(get_scene().render.fps * delta.total_seconds()) + 1


def save_as(file_name: str):
    file_path = "blend/" + file_name + ".blend"
    bpy.ops.wm.save_mainfile(filepath=file_path)


def driver_callable(func):
    func.driver_callable = True
    return func
