import bpy
from .object import BaseObject
from apeiron.globals.general import Vector, Euler
from abc import abstractmethod


class BaseEffect(BaseObject):
    """
    Base class from which all effects will derive.
    """
