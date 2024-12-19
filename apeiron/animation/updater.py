import bpy
from enum import Enum
from apeiron.primitives.points import Empty
from apeiron.animation.driver import Driver


class Updater:
    _pre_frame_set = False
    _post_frame_set = False

    class Type(Enum):
        PRE_FRAME_CHANGE = 1
        POST_FRAME_CHANGE = 2

    def __init__(self, type=Type.PRE_FRAME_CHANGE):
        self.handlers = None
        self.obj = Empty()
        self.obj['out'] = 0.0

        if type == Updater.Type.PRE_FRAME_CHANGE:
            assert not Updater._pre_frame_set, "The pre-frame-change handler is already set."
            self.handlers = bpy.app.handlers.frame_change_pre
            Updater._pre_frame_set = True
        elif type == Updater.Type.POST_FRAME_CHANGE:
            assert not Updater._post_frame_set, "The post-frame-change handler is already set."
            self.handlers = bpy.app.handlers.frame_change_post
            Updater._post_frame_set = True
        else:
            raise Exception('Unrecognised updater type.')

        self.handlers.clear()

    def add_input_variable(self, object, bl_data_path):
        """Adds an input variable."""

        d = Driver('dummy')
        d.set_output_variable(self.obj, '["out"]')
        d.add_input_variable('x', object, bl_data_path)
        d.set_expression('x')

    def add_function(self, function):
        """Adds a function as a handler."""
        self.handlers.append(function)
