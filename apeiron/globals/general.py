import bpy
import os
import sys
import math
from mathutils import Vector, Matrix, Euler
from datetime import timedelta
from typing import List
import apeiron.globals.easybpy as ebpy


UnitZ = Vector((0.0, 0.0, 1.0))
SMALL_OFFSET = 0.0001


class Ref:
    def __init__(self, value):
        self.value = value


def assert_2d(dim):
    assert dim == 2, "Can only handle 2D, currently."


def get_2d_vector(v=(0, 0)):
    return Vector(v).resized(2)


def get_3d_vector(v=(0, 0, 0)):
    return Vector(v).resized(3)


def rotate_90(vector, clockwise=False):
    assert math.isclose(0, vector.z), "This only applies in 2D."

    x = -vector.y
    y = vector.x
    vect = Vector((x, y, 0))
    if clockwise:
        vect *= -1

    return vect


def clear_scene():
    """Clears and deletes all current screen elements."""
    for obj in bpy.data.objects:
        bpy.data.objects.remove(obj, do_unlink=True)


def create_mesh(name: str, verts, faces=None, edges=None):
    """Creates and returns a mesh with a set of vertices, faces, and edges."""
    if edges is None:
        edges = []
    if faces is None:
        faces = []
    mesh = bpy.data.meshes.new(name)  # Create a new mesh
    mesh.from_pydata(verts, edges, faces)
    mesh.update()
    return mesh


def link_object(obj):
    bpy.data.collections['Collection'].objects.link(obj)


def add_object(name: str, data=None, parent=None):
    if not data:
        data = bpy.data.meshes.new(name=name)  # Create empty mesh
    obj = bpy.data.objects.new(name, data)
    obj.parent = parent
    link_object(obj)
    return obj


def add_empty(name='Empty', location=(0, 0, 0), parent=None):
    bpy.ops.object.empty_add(location=location, type='PLAIN_AXES')
    obj = bpy.context.object
    obj.name = name
    obj.parent = parent
    return obj


def add_empty_hook(name, parent, vertex_index):
    hook = ebpy.add_hook(parent)
    hook.object = add_empty(name, parent.data.vertices[vertex_index].co)
    hook.object.parent = parent
    hook.object.hide_viewport = True
    hook.object.hide_render = True
    hook.vertex_indices_set([vertex_index])
    return hook


def add_line_segment(name: str, point_0, point_1):
    # Create a new curve object
    curve_data = bpy.data.curves.new(name=name, type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.resolution_u = 1

    # Create a Bezier spline and add it to the curve
    spline = curve_data.splines.new(type='BEZIER')
    spline.bezier_points.add(count=1)
    for i, pt in enumerate([point_0, point_1]):
        spline.bezier_points[i].co = get_3d_vector(pt)

    return add_object(name, curve_data)


def add_circle(radius=1.0, centre=(0, 0, 0)):
    bpy.ops.curve.primitive_nurbs_circle_add(
        radius=radius, location=centre, scale=(1, 1, 1))
    return bpy.context.view_layer.objects.active


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
    return round(ebpy.get_scene().render.fps * delta.total_seconds()) + 1


def save_as(file_name: str):
    file_path = "blend/" + file_name + ".blend"
    bpy.ops.wm.save_mainfile(filepath=file_path)


def driver_callable(func):
    func.driver_callable = True
    return func


def is_blender_object(object):
    return hasattr(object, 'location') and hasattr(object, 'data')


def is_apeiron_object(object):
    from ..primitives.object import BaseObject
    return issubclass(type(object), BaseObject)


def get_blender_object(object):
    if is_blender_object(object):
        return object
    elif is_apeiron_object(object):
        return object.bl_obj
    else:
        raise Exception(f'Unrecognised object of type {type(object)}')


# Store the original stdout so we can restore it later
original_stdout = sys.stdout
original_stderr = sys.stderr


def disable_print():
    """Disable printing by redirecting sys.stdout to None."""
    sys.stdout = None
    sys.stderr = None


def enable_print():
    """Enable printing by restoring sys.stdout to its original state."""
    global original_stdout, original_stderr
    sys.stdout = original_stdout
    sys.stderr = original_stderr
