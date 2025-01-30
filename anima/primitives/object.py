import copy
import bpy
import math
from abc import ABC
from copy import deepcopy
from typing import Any, Optional
from anima.animation.driver import Driver
from anima.globals.easybpy import apply_scale
from anima.globals.general import create_mesh, Vector, Matrix, Euler, is_anima_object, add_object, \
    deepcopy_object, make_active, deselect_all, ebpy


class BaseObject(ABC):
    """
    Base class from which all visualisable objects will derive. Contains common members and methods, and
    encapsulates the underlying Blender object.
    """

    def __init__(self, *, bl_object=None, name='BaseObject', **kwargs):
        if kwargs:
            raise TypeError(f"Unexpected keyword arguments: {kwargs}")

        self.parent: type[BaseObject] = None
        self.children: list[type[BaseObject]] = []

        if bl_object is None:
            bl_object = add_object()
        bl_object.name = name
        self.bl_obj = bl_object
        self.shape_keys = []
        self.hooks = []
        self._write_logs = False

    def set_mesh(self, verts, faces, edges=None):
        """Sets the object's mesh based on lists of vertices, faces, and edges."""
        if edges is None:
            edges = []

        # Create mesh and create/update object.
        mesh = create_mesh(self.name + '_mesh', verts, faces, edges)
        self.bl_obj.data = mesh

    def update_mesh(self, verts, faces, edges=None):
        """Updates the object's mesh based on lists of vertices, faces, and edges."""
        if edges is None:
            edges = []
        mesh = self.bl_obj.data
        mesh.clear_geometry()
        mesh.from_pydata(verts, edges, faces)
        mesh.update()

    def update_vertices(self, verts):
        mesh = self.bl_obj.data
        assert len(verts) == len(mesh.vertices)
        for i, v in enumerate(verts):
            mesh.vertices[i].co = v

    def update_faces(self, faces):
        pass

    def add_object(self, object):
        """Adds an object of base type BaseObject and sets current object as parent."""
        assert is_anima_object(object), \
            "Can only add sub-objects of type BaseObject."
        object._set_parent(self)
        self.children.append(object)

    def add_keyframe(self, bl_data_path, index=-1, frame=bpy.context.scene.frame_current):
        """Adds a keframe for a given propety at the given frame."""
        self.bl_obj.keyframe_insert(bl_data_path, index=index, frame=frame)

    def add_handler(self, bl_data_path):
        pass

    def create_vertex_hook(self, name, vertex_index):
        """Create and return a hook for a given vertex in this object's mesh."""

        assert self._has_data(), f'The object {self.name} has no mesh set.'
        obj = self.bl_obj
        hook = ebpy.add_hook(obj)

        # Create empty. Note: Lazy import to prevent cyclic imports.
        from .points import Empty
        empty = Empty(location=obj.data.vertices[vertex_index].co,
                      parent=self, name=name)

        # Link the hook to the empty.
        hook.object = empty.object
        hook.vertex_indices_set([vertex_index])

        # Add empty as a child and store hook ref.
        self.add_object(empty)
        self.hooks.append(hook)

        # Todo - encapsulate hook in Hook class
        return empty

    def create_driver(self, bl_data_path, index=-1) -> Driver:
        """Create and return a driver for a given property in this object."""
        driver = Driver()
        driver.set_output_variable(self.bl_obj, bl_data_path, index)
        return driver

    def create_shape_key(self, name):
        """Create and return a shape key for this object."""
        shape_key = self.bl_obj.shape_key_add(name)
        self.shape_keys.append(shape_key)
        return shape_key

    def make_active(self):
        """Make this the current active object."""
        make_active(self.bl_obj)

    def make_inactive(self):
        """Make this object inactive."""
        deselect_all()

    def hide(self):
        """Hide this object and its children in both the viewport and the render."""
        self._set_visibility(False)
        for child in self.children:
            child.hide()

    def unhide(self):
        """Unhide this object and its children in both the viewport and the render."""
        self._set_visibility(True)
        for child in self.children:
            child.unhide()

    # Location-related methods ----------------------------------------------------------------------------- #

    def set_location(self, x=None, y=None, z=None, apply=False):
        """Sets the object's location in world space."""
        loc = self.location
        self.bl_obj.location = (x if x is not None else loc.x,
                                y if y is not None else loc.y,
                                z if z is not None else loc.z)
        if apply:
            ebpy.apply_location(ref=self.bl_obj)

    def translate(self, x=0, y=0, z=0, local=False, apply=False):
        """Translates the object in world/local space (defaults to world)."""
        self.make_active()
        ref_frame = 'LOCAL' if local else 'GLOBAL'
        bpy.ops.transform.translate(value=(x, y, z), orient_type=ref_frame)
        if apply:
            ebpy.apply_location(ref=self.bl_obj)

    @property
    def location(self):
        """Get the object's location."""
        return self.bl_obj.location

    @location.setter
    def location(self, loc):
        """Set the object's location."""
        self.set_location(*loc)

    # Rotation-related methods ----------------------------------------------------------------------------- #

    def set_rotation(self, x=None, y=None, z=None, apply=False):
        """Sets the object's rotation (Euler angles in radians) in world space."""
        obj = self.bl_obj
        rot = obj.rotation_euler
        obj.rotation_mode = 'XYZ'
        obj.rotation_euler = (x if x is not None else rot.x,
                              y if y is not None else rot.y,
                              z if z is not None else rot.z)
        if apply:
            ebpy.apply_rotation(ref=self.bl_obj)

    def rotate(self, x=0, y=0, z=0, local=False, apply=False):
        """Rotates the object by the given Euler angles (x, y, z) in world/local space (defaults to world)."""
        rotation = Euler((x, y, z), 'XYZ')
        if local:
            # bpy.ops.transform.rotate(
            #     value=0.597005, orient_axis='X', orient_type='LOCAL')

            self.bl_obj.rotation_euler.rotate(rotation)
        else:
            rotation_matrix = rotation.to_matrix().to_4x4()
            self.bl_obj.matrix_world = rotation_matrix @ self.world_matrix

        if apply:
            ebpy.apply_rotation(ref=self.bl_obj)

    def rotate_about(self, axis, local=False, apply=False):
        if apply:
            ebpy.apply_rotation(ref=self.bl_obj)

    def set_orientation(self, x_axis, y_axis, apply=False):
        x_axis = Vector(x_axis)
        y_axis = Vector(y_axis)
        assert math.isclose(x_axis.dot(y_axis), 0), "Axes are not orthogonal."

        # Compute orthonormal basis
        x_axis.normalize()
        y_axis.normalize()
        z_axis = x_axis.cross(y_axis)
        z_axis.normalize()

        # Create a 3x3 rotation matrix
        rot_matr = Matrix((
            x_axis,
            y_axis,
            z_axis
        )).transposed()

        # Convert to quaternion or Euler angles
        self.set_rotation(*rot_matr.to_euler(), apply)

    @property
    def rotation(self):
        """Get the object's rotation (Euler angles)."""
        return self.bl_obj.rotation_euler

    @rotation.setter
    def rotation(self, rot):
        """Set the object's rotation (Euler angles)."""
        self.set_rotation(*rot)

    @property
    def local_matrix(self):
        """Get the local matrix."""
        return self.bl_obj.matrix_local

    @local_matrix.setter
    def local_matrix(self, matrix):
        """Set the local matrix."""
        self.bl_obj.matrix_local = matrix

    @property
    def world_matrix(self):
        """Get the world matrix."""
        return self.bl_obj.matrix_world

    @world_matrix.setter
    def world_matrix(self, matrix):
        """Set the world matrix."""
        self.bl_obj.matrix_world = matrix

    # Scale-related methods -------------------------------------------------------------------------------- #

    def set_scale(self, x=None, y=None, z=None, apply=False):
        """Sets the object's scale."""
        scale = self.bl_obj.scale
        self.bl_obj.scale = (x if x is not None else scale.x,
                             y if y is not None else scale.y,
                             z if z is not None else scale.z)
        if apply:
            apply_scale(ref=self.bl_obj)

    def scale_by(self, x_fact=1.0, y_fact=1.0, z_fact=1.0, apply=False):
        """Scale the object by the given factors."""
        self.scale *= Vector((x_fact, y_fact, z_fact))
        if apply:
            apply_scale(ref=self.bl_obj)

    @property
    def scale(self):
        """Get the object's scale."""
        return self.bl_obj.scale

    @scale.setter
    def scale(self, scale):
        """Set the object's scale."""
        self.set_scale(*scale)

    # Property getters/setters for underlying blender object attributes ------------------------------------ #

    @property
    def name(self):
        """Get the object's name."""
        return self.bl_obj.name

    @name.setter
    def name(self, name):
        """Set the object's name."""
        self.bl_obj.name = name

    @property
    def vertices(self):
        """Get the mesh's vertices."""
        assert self._has_data(), f'The object {self.name} has no mesh set.'
        return self.bl_obj.data.vertices

    @property
    def faces(self):
        """Get the mesh's faces."""
        assert self._has_data(), f'The object {self.name} has no mesh set.'
        return self.bl_obj.data.polygons

    @property
    def edges(self):
        """Get the mesh's edges."""
        assert self._has_data(), f'The object {self.name} has no mesh set.'
        return self.bl_obj.data.edges

    @property
    def object(self):
        """Get the underlying Blender object."""
        return self.bl_obj

    # Debugging tools -------------------------------------------------------------------------------------- #

    def debug(self) -> bool:
        return self._write_logs

    def debug_on(self):
        self._write_logs = True

    def debug_off(self):
        self._write_logs = False

    # Magic methods ---------------------------------------------------------------------------------------- #

    def __getitem__(self, attr_name):
        """Get a custom property using the [] operator."""
        return self.bl_obj[attr_name]

    def __setitem__(self, attr_name, value):
        """Set a custom property using the [] operator."""
        self.bl_obj[attr_name] = value

    def __deepcopy__(self, memo: Optional[dict[int, Any]] = None):
        """Deepcopy the object."""
        if memo is None:
            memo = {}

        # Check if already deep-copied, to prevent recursion.
        self_id = id(self)
        if self_id in memo:
            return memo[self_id]

        # Create new instance without calling __init__ and cache.
        new_copy = self.__class__.__new__(self.__class__)
        memo[self_id] = new_copy

        # Copy all attributes except those in attrs_to_excl
        attrs_to_excl = self._deepcopy_excluded_attrs
        attrs_to_copy = {
            key: value for key, value in self.__dict__.items()
            if key not in attrs_to_excl
        }
        new_copy.__dict__.update(deepcopy(attrs_to_copy, memo))

        # Initialize excluded attributes as None
        for attr in attrs_to_excl:
            setattr(new_copy, attr, None)

        # Copy Blender object manually.
        new_copy.bl_obj = deepcopy_object(self.bl_obj)

        return new_copy

    @property
    def _deepcopy_excluded_attrs(self) -> set[str]:
        """Attributes to exclude from deep copying."""
        assert len(self.shape_keys) == 0, \
            'Cannot deepcopy objects with shape keys yet.'
        assert len(self.hooks) == 0, \
            'Cannot deepcopy objects with hooks yet.'
        return {'bl_obj', 'shape_keys', 'hooks', 'parent'}

    # Private methods -------------------------------------------------------------------------------------- #

    def _has_data(self):
        """Does the Blender object have data?"""
        return self.bl_obj.data is not None

    def _set_parent(self, parent):
        """Sets the parent (of type BaseObject) of the current object."""
        assert is_anima_object(parent), \
            "Can only set a parent of type BaseObject."
        self.parent = parent
        self.bl_obj.parent = parent.bl_obj

    def _set_visibility(self, val):  # True if visible, else False
        """Sets the object's visibility in both the viewport and render."""
        self._set_viewport_visibility(val)
        self._set_render_visibility(val)

    def _set_viewport_visibility(self, val):  # True if visible, else False
        """Sets the object's visibility in the viewport."""
        self.bl_obj.hide_viewport = not val

    def _set_render_visibility(self, val):  # True if visible, else False
        """Sets the object's visibility in the render."""
        self.bl_obj.hide_render = not val

    def _log_info(self, visitor):
        print(f'Object {self.name} logs:')
        if self._write_logs:
            visitor(self)


class CustomObject(BaseObject):
    def __init__(self, bl_object, name='Custom', **kwargs):
        assert bl_object is not None, 'Must specify underlying blender object.'
        super().__init__(bl_object=bl_object, name=name, **kwargs)
