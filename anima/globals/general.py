import bpy
import os
import sys
import math
from copy import deepcopy
from typing import Iterable
from mathutils import Vector, Matrix, Euler
from datetime import timedelta
import anima.globals.easybpy as ebpy


UnitZ = Vector((0.0, 0.0, 1.0))
SMALL_OFFSET = 0.00005
DEFAULT_ABSOLUTE_SMALL = 1e-7
DEFAULT_RELATIVE_SMALL = 1e-8


def clip(val: int | float, min_val: int | float, max_val: int | float):
    return min(max(val, min_val), max_val)


def reciprocal(val: int | float, if_val_0: int | float = 0):
    return 1 / val if not math.isclose(val, 0) else if_val_0


def assert_2d(dim):
    assert dim == 2, "Can only handle 2D, currently."


def get_2d_vector(v=(0, 0)):
    return Vector(v).resized(2)


def get_3d_vector(v=(0, 0, 0)):
    return Vector(v).resized(3)


def rotate_90(vector: Vector, clockwise=False):
    assert math.isclose(0, vector.z), "This only applies in 2D."

    x = -vector.y
    y = vector.x
    vect = Vector((x, y, 0))
    if clockwise:
        vect *= -1

    return vect


def are_vectors_close(v_1: Vector | Iterable, v_2: Vector | Iterable, rel_tol: float = DEFAULT_RELATIVE_SMALL,
                      abs_tol: float = DEFAULT_ABSOLUTE_SMALL):
    for a_1, a_2 in zip(v_1, v_2):
        if not math.isclose(a_1, a_2, rel_tol=rel_tol, abs_tol=abs_tol):
            return False
    return True


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


def add_object(name: str = 'Object', data=None, parent=None):
    if data is None:
        data = bpy.data.meshes.new(name=name)  # Create empty mesh
    obj = bpy.data.objects.new(name, data)
    obj.parent = parent
    link_object(obj)
    return obj


def deepcopy_object(obj, name=None):
    if obj is None:
        return None
    new_obj = obj.copy()
    new_obj.name = deepcopy(obj.name) if name is None else name
    if obj.data is not None:
        new_obj.data = obj.data.copy()
    link_object(new_obj)
    return new_obj


def add_empty(name='Empty', location=(0, 0, 0), parent=None):
    bpy.ops.object.empty_add(location=location, type='PLAIN_AXES')
    obj = bpy.context.object
    obj.name = name
    obj.parent = parent
    return obj


def make_active(obj):
    bpy.context.view_layer.objects.active = obj
    deselect_all()
    obj.select_set(True)


def active_object():
    return bpy.context.view_layer.objects.active


def deselect_all():
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = None


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


def add_circle(radius: float = 1, centre=(0, 0, 0)):
    bpy.ops.curve.primitive_nurbs_circle_add(
        radius=radius, location=centre, scale=(1, 1, 1))
    return active_object()


def add_square(size: float = 1, location=(0, 0, 0)):
    bpy.ops.mesh.primitive_plane_add(size=size, location=location)
    return active_object()


def add_cube(size: float = 1, location=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=size, location=(0, 0, 0))
    return active_object()


def add_cuboid(length: float, width: float, height: float, location=(0, 0, 0)):
    cube = add_cube()
    cube.scale = (length, width, height)
    return cube


def set_mode(mode: str):
    bpy.ops.object.mode_set(mode=mode)


def set_edit_mode():
    set_mode('EDIT')


def set_object_mode():
    set_mode('OBJECT')


def flip_normals_active_obj():
    set_edit_mode()
    bpy.ops.mesh.flip_normals()
    set_object_mode()


def extrude_active_obj(displacement: Vector):
    set_edit_mode()
    bpy.ops.mesh.extrude_region_move(
        TRANSFORM_OT_translate={"value": displacement})
    set_object_mode()


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


def is_anima_object(object):
    from ..primitives.object import BaseObject
    return issubclass(type(object), BaseObject)


def get_blender_object(object):
    if is_blender_object(object):
        return object
    elif is_anima_object(object):
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
