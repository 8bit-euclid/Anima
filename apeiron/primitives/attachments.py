import bpy
from .object import BaseObject
from apeiron.globals.general import Vector, Euler
from abc import ABC, abstractmethod


class BaseAttachment(BaseObject):
    """
    Base class from which all attachments (joint, cap) will derive.
    """

    def __init__(self, bl_object, name='BaseAttachment'):
        super().__init__(bl_object, name)
        self.connections = []  # of base type BaseCurve

    @abstractmethod
    def offset_length(self):
        pass
