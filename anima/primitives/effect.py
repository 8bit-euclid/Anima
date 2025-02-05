import bpy
from .object import Object
from anima.globals.general import Vector, Euler
from abc import abstractmethod


class Effect(Object):
    """
    Base class from which all effects will derive.
    """
