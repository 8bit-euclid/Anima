import bpy
from .object import BaseObject
from anima.globals.general import Vector, Euler
from abc import abstractmethod


class BaseEffect(BaseObject):
    """
    Base class from which all effects will derive.
    """
