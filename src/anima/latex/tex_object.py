from __future__ import annotations

from anima.primitives.object import Object


class TeXObject(Object):
    """Base class for all TeX objects, which can be either a command or a text object."""

    def __init__(self, name: str | None = None, parent: TeXObject | None = None):
        super().__init__(name=name, parent=parent)
        self.text: str = ""
        self.rendered: bool = True
        self.sub_objects: tuple = ()

    def add_child(self, object: TeXObject):
        """Adds an object (of type TeXObject) as a child and sets current object as its parent.

        Args:
            object (TeXObject): The child object to add.

        Raises:
            TypeError: If the object is not a TeXObject instance.
        """
        if not isinstance(object, TeXObject):
            raise TypeError("Can only add TeXObject instances")
        super().add_child(object)
