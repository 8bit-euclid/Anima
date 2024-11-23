from abc import abstractmethod
from enum import Enum
from .curves import BaseCurve
from .attachments import BaseAttachment


class Joint(BaseAttachment, BaseCurve):
    """
    Todo
    """

    class Type(Enum):
        MITER = 1
        ROUND = 2
        BEVEL = 3
        POINT = 4

    def __init__(self, bl_object=None, name='Joint'):
        super().__init__(name, bl_object)
