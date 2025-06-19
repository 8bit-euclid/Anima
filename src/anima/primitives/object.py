import bpy
import math
from abc import ABC
from copy import deepcopy
from typing import Any, Optional
from anima.globals.easybpy import apply_scale
from anima.globals.general import Vector, Matrix, Euler, is_animable, add_object, \
    deepcopy_object, make_active, deselect_all, ebpy, outer_product


class Object(ABC):
    """
    Base class for all animable objects. Encapsulates the underlying Blender object and provides
    common members and methods for manipulation, parenting, transformation, and animation.
    All subclasses should use cooperative inheritance (i.e., call super()) to maintain the correct
    method resolution order (MRO), especially in multiple inheritance scenarios.
    See: https://docs.python.org/3/library/functions.html#super for more details.
    """

    def __init__(self, *, bl_object=None, name='Object', **kwargs):
        # There should be no additional keyword arguments (assuming cooperative inheritance).
        if kwargs:
            raise TypeError(f"Unexpected keyword arguments: {kwargs}")

        self.parent: type[Object] = None
        self.children: list[type[Object]] = []

        if bl_object is None:
            bl_object = add_object(name=name)
        bl_object.name = name
        self._bl_object = bl_object
        self.shape_keys = []
        self._write_logs = False

    def add_subobject(self, object):
        """Adds a sub-object (of type BaseObject) as a child and sets current object as its parent.
        Args:
            object (BaseObject): The sub-object to add.
        Raises:
            AssertionError: If the object is not animable.
        """
        assert is_animable(object), "Can only add animable sub-objects."
        object._set_parent(self)
        self.children.append(object)

    def add_keyframe(self, bl_data_path, index=-1, frame=None):
        """Add a keframe for the specified object propety at the given frame.
        Args:
            bl_data_path (str): The Blender data path to the property to keyframe.
            index (int, optional): The index of the property to keyframe. Defaults to -1.
            frame (int, optional): The frame at which to insert the keyframe. Defaults to the current frame"""
        if frame is None:
            frame = bpy.context.scene.frame_current
        assert isinstance(frame, int), "Frame must be an integer."
        assert hasattr(self.object, bl_data_path), \
            f"Invalid data path: {bl_data_path}"
        self.object.keyframe_insert(bl_data_path, index=index, frame=frame)

    def add_handler(self, handler):
        """Add a handler for the specified object property.
        Args:
            handler (function): The handler function to add"""
        pass

    def create_shape_key(self, name):
        """Create and return a shape key for this object.
        Args:
            name (str): The name of the shape key to create.
        Returns:
            bpy.types.ShapeKey: The created shape key.
        """
        shape_key = self._bl_object.shape_key_add(name)
        self.shape_keys.append(shape_key)
        return shape_key

    def make_active(self):
        """Make this the current active object."""
        make_active(self.object)

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

    def copy(self):
        """Get a deep copy of this object."""
        return deepcopy(self)

    # Location-related methods ----------------------------------------------------------------------------- #

    def set_location(self, x=None, y=None, z=None, apply=False):
        """Sets the object's location in world space.
        Args:
            x (float, optional): The x-coordinate of the location. Defaults to None.
            y (float, optional): The y-coordinate of the location. Defaults to None.
            z (float, optional): The z-coordinate of the location. Defaults to None.
            apply (bool, optional): If True, permanently apply the location to the object. Defaults to False.
        Raises:
            AssertionError: If no location dimension is specified (x, y, or z).
        """
        x_set = x is not None
        y_set = y is not None
        z_set = z is not None
        assert x_set or y_set or z_set, "At least one location dimension must be specified."
        loc = self.location
        self._bl_object.location = (x if x_set else loc.x,
                                    y if y_set else loc.y,
                                    z if z_set else loc.z)
        if apply:
            ebpy.apply_location(ref=self.object)

    def translate(self, x: float = 0, y: float = 0, z: float = 0, local: bool = False, apply: bool = False):
        """Translates the object in world/local space (defaults to world).
        Args:
            x (float, optional): The translation in the x dimension. Defaults to 0.
            y (float, optional): The translation in the y dimension. Defaults to 0.
            z (float, optional): The translation in the z dimension. Defaults to 0.
            local (bool, optional): If True, translates in local space; otherwise, translates in world space. Defaults to False.
            apply (bool, optional): If True, permanently apply the translation to the object. Defaults to False.
        """
        self.make_active()
        ref_frame = 'LOCAL' if local else 'GLOBAL'
        bpy.ops.transform.translate(value=(x, y, z), orient_type=ref_frame)
        if apply:
            ebpy.apply_location(ref=self.object)

    @property
    def location(self):
        """Get the object's location.
        Returns:
            tuple: A 3D Vector representing the location in x, y, z dimensions."""
        return self._bl_object.location

    @location.setter
    def location(self, loc):
        """Set the object's location.
        Args:
            loc (tuple or list): A tuple or list of 3 floats representing the location in x, y, z dimensions.
        """
        self.set_location(*loc)

    # Rotation-related methods ----------------------------------------------------------------------------- #

    def set_rotation(self, x=None, y=None, z=None, apply=False):
        """Sets the object's rotation (Euler angles in radians) in world space.
        Args:
            x (float, optional): The rotation angle around the x-axis in radians. Defaults to None.
            y (float, optional): The rotation angle around the y-axis in radians. Defaults to None.
            z (float, optional): The rotation angle around the z-axis in radians. Defaults to None.
            apply (bool, optional): If True, permanently apply the rotation to the object. Defaults to False.
        Raises:
            AssertionError: If no rotation dimension is specified (x, y, or z).
        """
        x_set = x is not None
        y_set = y is not None
        z_set = z is not None
        assert x_set or y_set or z_set, "At least one rotation dimension must be specified."
        obj = self._bl_object
        rot = obj.rotation_euler
        obj.rotation_mode = 'XYZ'
        obj.rotation_euler = (x if x_set else rot.x,
                              y if y_set else rot.y,
                              z if z_set else rot.z)
        if apply:
            ebpy.apply_rotation(ref=self.object)

    def rotate(self, x: float = 0, y: float = 0, z: float = 0, local: bool = False, apply: bool = False):
        """Rotates the object by the given Euler angles (x, y, z) in world/local space (defaults to world).
        Args:
            x (float, optional): The rotation angle around the x-axis in radians. Defaults to 0.
            y (float, optional): The rotation angle around the y-axis in radians. Defaults to 0.
            z (float, optional): The rotation angle around the z-axis in radians. Defaults to 0.
            local (bool, optional): If True, rotates in local space; otherwise, rotates in world space. Defaults to False.
            apply (bool, optional): If True, permanently apply the rotation to the object. Defaults to False.
        """
        rotation = Euler((x, y, z), 'XYZ')
        if local:
            self._bl_object.rotation_euler.rotate(rotation)
        else:
            rotation_matrix = rotation.to_matrix().to_4x4()
            self.object.matrix_world = rotation_matrix @ self.world_matrix

        if apply:
            ebpy.apply_rotation(ref=self.object)

    def rotate_about(self, axis: tuple | list[float] | Vector, local: bool = False, apply: bool = False):
        """Rotates the object about a given axis.
        Args:
            axis: The axis of rotation, specified as a tuple/list/Vector of 2/3 floats or a Vector.
            local (bool, optional): If True, rotates in local space; otherwise, rotates in world space. Defaults to False.
            apply (bool, optional): If True, permanently apply the rotation to the object. Defaults to False.
        """
        raise NotImplementedError(
            "The rotate_about method is not implemented yet. ")
        if apply:
            ebpy.apply_rotation(ref=self.object)

    def set_orientation(self, x_axis: tuple | list[float] | Vector,
                        y_axis: tuple | list[float] | Vector, apply: bool = False):
        """Sets the object's orientation based on two orthogonal axes.
        Args:
            x_axis: A tuple/list/Vector of 2/3 floats representing the x-axis direction.
            y_axis: A tuple/list/Vector of 2/3 floats representing the y-axis direction.
            apply (bool, optional): If True, permanently apply the rotation to the object. Defaults to False.
        Raises:
            AssertionError: If the axes are not orthogonal.
        """
        x_axis = Vector(x_axis)
        y_axis = Vector(y_axis)
        assert math.isclose(x_axis.dot(y_axis), 0), \
            "X and Y axes are not orthogonal."

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
        """Get the object's rotation (Euler angles).
        Returns:
            tuple: A 3D Vector representing the rotation in Euler angles."""
        return self._bl_object.rotation_euler

    @rotation.setter
    def rotation(self, rot):
        """Set the object's rotation (Euler angles).
        Args:
            rot (tuple or list): A tuple or list of 3 floats representing the rotation in Euler angles.
        """
        self.set_rotation(*rot)

    @property
    def local_matrix(self):
        """Get the local matrix.
        Returns:
            Matrix: The local matrix of the object."""
        return self._bl_object.matrix_local

    @local_matrix.setter
    def local_matrix(self, matrix):
        """Set the local matrix.
        Args:
            matrix (Matrix): The new local matrix to set for the object."""
        self._bl_object.matrix_local = matrix

    @property
    def world_matrix(self):
        """Get the world matrix.
        Returns:
            Matrix: The world matrix of the object."""
        return self._bl_object.matrix_world

    @world_matrix.setter
    def world_matrix(self, matrix):
        """Set the world matrix.
        Args:
            matrix (Matrix): The new world matrix to set for the object."""
        self._bl_object.matrix_world = matrix

    # Scale-related methods -------------------------------------------------------------------------------- #

    def set_scale(self, x: float = None, y: float = None, z: float = None, apply: bool = False):
        """Sets the object's scale.
        Args:
            x (float, optional): The scale in the x dimension. Defaults to None.
            y (float, optional): The scale in the y dimension. Defaults to None.
            z (float, optional): The scale in the z dimension. Defaults to None.
            apply (bool, optional): If True, permanently apply the scale to the object. Defaults to False.
        Raises:
            AssertionError: If no scale dimension is specified (x, y, or z).
        """
        x_set = x is not None
        y_set = y is not None
        z_set = z is not None
        assert x_set or y_set or z_set, "At least one scale dimension must be specified."
        scale = self._bl_object.scale
        self._bl_object.scale = (x if x_set else scale.x,
                                 y if y_set else scale.y,
                                 z if z_set else scale.z)
        if apply:
            apply_scale(ref=self.object)

    def scale_by(self, x_fact: float = 1.0, y_fact: float = 1.0, z_fact: float = 1.0, apply: bool = False):
        """Scale the object by the given factors.
        Args:
            x_fact (float, optional): The factor by which to scale in the x dimension. Defaults to 1.0.
            y_fact (float, optional): The factor by which to scale in the y dimension. Defaults to 1.0.
            z_fact (float, optional): The factor by which to scale in the z dimension. Defaults to 1.0.
            apply (bool, optional): If True, permanently apply the scale to the object. Defaults to False."""
        self.scale *= Vector((x_fact, y_fact, z_fact))
        if apply:
            apply_scale(ref=self.object)

    @property
    def scale(self):
        """Get the object's scale.
        Returns:
            tuple: A tuple of 3 floats representing the scale in x, y, z dimensions."""
        return self._bl_object.scale

    @scale.setter
    def scale(self, scale):
        """Set the object's scale.
        Args:
            scale (tuple or list): A tuple or list of 3 floats representing the scale in x, y, z dimensions"""
        self.set_scale(*scale)

    # Other geometric operations --------------------------------------------------------------------------- #

    def reflect(self, plane_normal, plane_point=(0, 0, 0)):
        """ Reflects an object about an arbitrary plane. """
        plane_normal = Vector(plane_normal).normalized()
        plane_point = Vector(plane_point)

        # Compute reflection matrix
        N = outer_product(plane_normal, plane_normal)
        I = Matrix.Identity(3)
        R = I - 2 * N  # Reflection matrix

        # Convert to 4x4 transformation matrix
        refl_matrix = Matrix.Translation(
            plane_point) @ R.to_4x4() @ Matrix.Translation(-plane_point)

        # Apply transformation
        self.world_matrix = refl_matrix @ self.world_matrix

    # Property getters/setters for underlying blender object attributes ------------------------------------ #

    @property
    def name(self):
        """Get the object's name.
        Returns:
            str: The name of the object."""
        return self._bl_object.name

    @name.setter
    def name(self, name):
        """Set the object's name.
        Args:
            name (str): The new name for the object."""
        self._bl_object.name = name

    @property
    def object(self):
        """Get the underlying Blender object."""
        return self._bl_object

    # Debugging tools -------------------------------------------------------------------------------------- #

    def debug(self) -> bool:
        """Check if debugging is enabled for this object.
        Returns:
            bool: True if debugging is enabled, else False."""
        return self._write_logs

    def debug_on(self):
        """Turn on debugging for this object."""
        self._write_logs = True

    def debug_off(self):
        """Turn off debugging for this object."""
        self._write_logs = False

    # Magic methods ---------------------------------------------------------------------------------------- #

    def __getitem__(self, attr_name):
        """Get a custom property using the [] operator.
        Args:
            attr_name (str): The name of the custom property to get.
        Returns:
            Any: The value of the custom property."""
        return self._bl_object[attr_name]

    def __setitem__(self, attr_name, value):
        """Set a custom property using the [] operator.
        Args:
            attr_name (str): The name of the custom property to set.
            value (Any): The value to set for the custom property."""
        self._bl_object[attr_name] = value

    def __deepcopy__(self, memo: Optional[dict[int, Any]] = None):
        """Deepcopy all contents of the object except those in _deepcopy_excluded_attrs().
        Args:
            memo (dict[int, Any], optional): A memo dictionary to keep track of already copied objects.
                Defaults to None.
        Returns:
            BaseObject: A new instance of the object with all attributes copied, except those specified in
                `_deepcopy_excluded_attrs()`.
        """
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
        attrs_to_excl = self._deepcopy_excluded_attrs()
        attrs_to_copy = {
            key: value for key, value in self.__dict__.items()
            if key not in attrs_to_excl
        }
        new_copy.__dict__.update(deepcopy(attrs_to_copy, memo))

        # Initialize excluded attributes as None
        for attr in attrs_to_excl:
            setattr(new_copy, attr, None)

        # Copy Blender object manually.
        new_copy._bl_object = deepcopy_object(self.object)

        return new_copy

    def _deepcopy_excluded_attrs(self) -> set[str]:
        """Attributes to exclude from deep copying.
        Returns:
            set[str]: A set of attribute names to exclude from deep copying."""
        assert len(self.shape_keys) == 0, \
            'Cannot deepcopy objects with shape keys yet.'
        return {'_bl_object', 'shape_keys', 'parent'}

    # Private methods -------------------------------------------------------------------------------------- #

    def _has_data(self):
        """Does the Blender object have data?
        Returns:
            bool: True if the Blender object has data, else False.
        Raises:
            AssertionError: If the Blender object is not set."""
        assert self._bl_object is not None, \
            "The Blender object is not set. Cannot check for data."
        return self._bl_object.data is not None

    def _set_parent(self, parent: type['Object']):
        """Sets the parent (of type BaseObject) of the current object.
        Args:
            parent (BaseObject): The parent object to set.
        Raises:
            AssertionError: If the parent is not of type BaseObject."""
        assert is_animable(parent), \
            "Can only set a parent of type BaseObject."
        self.parent = parent
        self._bl_object.parent = parent._bl_object

    def _set_visibility(self, val: bool):
        """Sets the object's visibility in both the viewport and render.
        Args:
            val (bool): True if the object should be visible, else False."""
        self._set_viewport_visibility(val)
        self._set_render_visibility(val)

    def _set_viewport_visibility(self, val: bool):
        """Sets the object's visibility in the viewport.
        Args:
            val (bool): True if the object should be visible in the viewport, else False."""
        self._bl_object.hide_viewport = not val

    def _set_render_visibility(self, val: bool):
        """Sets the object's visibility in the render.
        Args:
            val (bool): True if the object should be visible in the render, else False."""
        self._bl_object.hide_render = not val

    def _log_info(self, visitor: callable):
        """Logs information about the object using the provided visitor function.
        Args:
            visitor (callable): A function that takes the object as an argument and logs its information."""
        print(f'Object {self.name} logs:')
        if self._write_logs:
            visitor(self)


class CustomObject(Object):
    def __init__(self, bl_object, name='Custom', **kwargs):
        assert bl_object is not None, 'Must specify underlying blender object.'
        super().__init__(bl_object=bl_object, name=name, **kwargs)
