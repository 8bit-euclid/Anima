from abc import abstractmethod

import bpy

from anima.globals.general import Euler, Vector

from .object import Object


class Effect(Object):
    """
    Base class from which all effects will derive.
    """
