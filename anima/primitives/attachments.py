from .object import BaseObject
from abc import abstractmethod


class BaseAttachment(BaseObject):
    """
    Base class from which all attachments (joint, cap) will derive.
    """

    def __init__(self, bl_object=None, connections=None, name='BaseAttachment', **kwargs):
        super().__init__(bl_object=bl_object, name=name, **kwargs)
        self.connections = \
            connections if connections is not None else []  # of base type BaseCurve

    @abstractmethod
    def offset_distance(self):
        pass
