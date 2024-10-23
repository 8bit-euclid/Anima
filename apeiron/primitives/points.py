from apeiron.globals.general import *
from apeiron.primitives.base import BaseObject
import bpy


class Empty(BaseObject):
    """
    An object with just a point location and no mesh. It is invisible in the final render and can be used as 
    reference points for other geometry or as a hook that drives some geometric property.  
    """

    def __init__(self, name='Empty', location=(0, 0, 0), parent=None):
        # Types: PLAIN_AXES, ARROWS, SINGLE_ARROW, CIRCLE, CUBE, SPHERE
        bpy.ops.object.empty_add(location=location, type='SINGLE_ARROW')
        obj = bpy.context.object

        super().__init__(name, obj)
        self.location = location
        if parent:
            self._set_parent(parent)
        self.hide()

    def _process_action(self, action):
        super()._process_action(action)
        raise Exception('Implement')


class Point(BaseObject):
    """
    A point object that is visible in both the viewport and the render.
    """

    def __init__(self, name='Point', location=(0, 0, 0), parent=None):
        super().__init__(name, create_object(name))
        self.location = location
        if parent:
            self._set_parent(parent)

        # Note: the vertex's coordinates are expressed in the point's local coordinate system.
        self.set_mesh([(0, 0, 0)], faces=[])

    def _process_action(self, action):
        super()._process_action(action)
        raise Exception('Implement')
