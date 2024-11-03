# from apeiron.globals.general import *
import bpy
from apeiron.globals.general import create_mesh, Vector, Euler, is_apeiron_object, ebpy
from apeiron.animation.driver import Driver
from apeiron.animation.action import Action
from abc import ABC, abstractmethod


class BaseObject(ABC):
    """
    Base class from which all visualisable objects will derive. Contains common functionality and 
    enforces that all subclasses must implement the '_process_action' method. Encapsulates the underlying 
    Blender object.
    """

    def __init__(self, name='BaseObject', bl_object=None, actions=None):
        self.name = name
        self.bl_obj = bl_object
        self.parent = None  # of base type BaseObject
        self.children = []  # of base type BaseObject

        if actions is None:
            actions = []
        self.actions = actions

        self.shape_keys = []
        self.hooks = []

    @abstractmethod
    def _process_action(self, action: Action):
        """Must be implemented by all sub-classes, to process each Action.Type."""
        pass

    def set_mesh(self, vertices, faces, edges=[]):
        """Sets the object's mesh based on lists of vertices, faces, and edges."""
        self.bl_obj.data = create_mesh("mesh", vertices, faces, edges)

    def set_location(self, x=None, y=None, z=None):
        """Sets the object's location in world space."""
        loc = self.location
        self.bl_obj.location = (x if x is not None else loc.x,
                                y if y is not None else loc.y,
                                z if z is not None else loc.z)

    def set_rotation(self, x=None, y=None, z=None):
        """Sets the object's rotation (Euler angles) in world space."""
        rot = self.rotation_euler
        self.bl_obj.rotation_euler = (x if x is not None else rot.x,
                                      y if y is not None else rot.y,
                                      z if z is not None else rot.z)

    def set_scale(self, x=None, y=None, z=None):
        """Sets the object's scale."""
        scale = self.bl_obj.scale
        self.bl_obj.scale = (x if x is not None else scale.x,
                             y if y is not None else scale.y,
                             z if z is not None else scale.z)

    def translate(self, x=0, y=0, z=0, local=False):
        """Translates the object in world/local space (defaults to world)."""
        translation = Vector((x, y, z))
        if local:
            self.bl_obj.location += self.world_matrix.to_quaternion() @ translation
        else:
            self.bl_obj.location += translation

    def rotate(self, x=0, y=0, z=0, local=False):
        """Rotates the object by the given Euler angles (x, y, z) in world/local space (defaults to world)."""
        rotation = Euler((x, y, z), 'XYZ')
        if local:
            self.bl_obj.rotation_euler.rotate(rotation)
        else:
            rotation_matrix = rotation.to_matrix().to_4x4()
            self.bl_obj.matrix_world = rotation_matrix @ self.world_matrix()

    def scale_by(self, x_fact=1.0, y_fact=1.0, z_fact=1.0):
        """Scale the object by the given factors."""
        self.scale *= Vector((x_fact, y_fact, z_fact))

    def add_action(self, action):
        """Todo - do we really need this?"""
        self.actions.append(action)

    def add_object(self, object):
        """Adds an object of base type BaseObject and sets current object as parent."""
        assert is_apeiron_object(object), \
            "Can only add sub-objects of type BaseObject."
        object._set_parent(self)
        self.children.append(object)

    def add_keyframe(self, bl_data_path, index=-1, frame=bpy.context.scene.frame_current):
        """Adds a keframe for a given propety at the given frame."""
        self.bl_obj.keyframe_insert(bl_data_path, index, frame)

    def create_vertex_hook(self, name, vertex_index):
        """Create and return a hook for a given vertex in this object's mesh."""

        assert self._has_data(), f'The object {self.name} has no mesh set.'
        obj = self.bl_obj
        hook = ebpy.add_hook(obj)

        # Create empty. Note: Lazy import to prevent cyclic imports.
        from .points import Empty
        empty = Empty(name, location=obj.data.vertices[vertex_index].co,
                      parent=self)

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

    def hide(self):
        """Hide this object in both the viewport and the render."""
        self._set_visibility(False)

    def unhide(self):
        """Unhide this object in both the viewport and the render."""
        self._set_visibility(True)

    def process_actions(self):
        """Process all actions to be performed by this object."""
        for action in self.actions:
            self._process_action(action)

    # Property getters/setters for underlying blender object attributes.
    @property
    def location(self):
        """Get the object's location."""
        return self.bl_obj.location

    @location.setter
    def location(self, loc):
        """Set the object's location."""
        self.set_location(*loc)

    @property
    def rotation(self):
        """Get the object's rotation (Euler angles)."""
        return self.bl_obj.rotation_euler

    @rotation.setter
    def rotation(self, rot):
        """Set the object's rotation (Euler angles)."""
        self.set_rotation(*rot)

    @property
    def scale(self):
        """Get the object's scale."""
        return self.bl_obj.scale

    @scale.setter
    def scale(self, scale):
        """Set the object's scale."""
        self.set_scale(*scale)

    @property
    def world_matrix(self):
        """Get the world matrix."""
        return self.bl_obj.matrix_world

    @world_matrix.setter
    def world_matrix(self, matrix):
        """Set the world matrix."""
        self.bl_obj.matrix_world = matrix

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

    # Operator overloads
    def __getitem__(self, key):
        """Get a custom property using the [] operator."""
        return self.bl_obj[key]

    def __setitem__(self, key, value):
        """Set a custom property using the [] operator."""
        self.bl_obj[key] = value

    # Private methods
    def _has_data(self):
        """Does the object have data?"""
        return self.bl_obj.data is not None

    def _set_parent(self, parent):
        """Sets the parent (of type BaseObject) of the current object."""
        assert is_apeiron_object(parent), \
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
