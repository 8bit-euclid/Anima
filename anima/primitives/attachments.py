from .object import Object
from abc import abstractmethod


class Attachment(Object):
    """
    Base class from which all attachments (joint, cap) derive.
    """

    def __init__(self, bl_object=None, connections=None, name='BaseAttachment', **kwargs):
        super().__init__(bl_object=bl_object, name=name, **kwargs)
        self.connections = \
            connections if connections is not None else []  # entries of base type BaseCurve

    @abstractmethod
    def offset_distance(self) -> float:
        """The distance by which this attachment should be offset from the parent object."""
        pass
