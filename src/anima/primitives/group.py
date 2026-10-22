from __future__ import annotations

from collections.abc import Iterable

from anima.globals.general import add_empty
from anima.primitives.object import Object


class Group(Object):
    """A data-less container that applies Object operations to several objects at once.

    Members become children, so every `Object` method that recurses over children (materials, textures,
    visibility, ...) works on the group without any forwarding code. The group is a Blender empty with no data,
    and members are parented to it, so keep its own transform at the identity unless you want to move them all.
    Its axes are hidden in the viewport; use `highlight()` to outline the members while debugging.
    """

    def __init__(
        self,
        objects: Iterable[Object] = (),
        *,
        name: str = "Group",
        parent: Object | None = None,
    ) -> None:
        """Initialise the group.

        Args:
            objects: Objects to add as children. Each can belong to only one parent.
            name: The name of the group.
            parent: The parent object. Defaults to None.
        """
        bl_object = add_empty(name)
        bl_object.empty_display_size = 0
        super().__init__(bl_object=bl_object, name=name, parent=parent)
        self.add(*objects)

    def add(self, *objects: Object) -> Group:
        """Add objects as children of the group.

        Args:
            *objects: The objects to add.

        Returns:
            Group: This group.

        Raises:
            ValueError: If an object already belongs to another parent; call `remove_child()` on its
                current parent first.
        """
        self.add_children(*objects)
        return self
