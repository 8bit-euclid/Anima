import bpy
from .object import BaseObject
from apeiron.globals.general import Vector, Euler
from abc import ABC, abstractmethod


class BaseEffect(BaseObject, ABC):
    """
    Base class from which all effects will derive.
    """
