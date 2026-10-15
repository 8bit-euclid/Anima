from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

import bpy
from mathutils import Vector

from anima.globals.general import create_mesh, ebpy
from anima.primitives.object import Object

if TYPE_CHECKING:
    from anima.primitives.points import Empty

_Vertex = Sequence[float] | Vector
_Vertices = Sequence[_Vertex]
_Face = Sequence[int]
_Faces = Sequence[_Face]
_Edges = Sequence[Sequence[int]]


class Mesh(Object):
    """A class representing a mesh object in Blender."""

    def __init__(
        self,
        bl_object: bpy.types.Object | None = None,
        name: str = "Mesh",
        **kwargs: Any,
    ) -> None:
        """Initializes the Mesh object.

        Args:
            bl_object (bpy.types.Object, optional): The Blender object to wrap. Defaults to None.
            name (str, optional): The name of the mesh object. Defaults to 'Mesh'.
            **kwargs: Additional keyword arguments passed to the parent class.
        """
        if bl_object is not None:
            assert bl_object.type == "MESH", f"Expected a mesh but got a {bl_object.type}"
        super().__init__(bl_object=bl_object, name=name, **kwargs)

        self._hooks = []

    def set_mesh(self, verts: _Vertices, faces: _Faces, edges: _Edges | None = None) -> None:
        """Sets the object's mesh based on lists of vertices, faces, and edges.

        Args:
            verts: Vertex coordinates, each supplied as a tuple, list, or mathutils.Vector of 2 or 3 floats.
            faces: Faces described by sequences of vertex indices.
            edges: Edges described by sequences of vertex indices. Defaults to None.
        """
        if edges is None:
            edges = []

        # Preserve any materials assigned to the old mesh data, since it is about to be replaced.
        old_materials = list(self.object.data.materials) if self._has_data() else []

        # Create mesh and create/update object.
        mesh = create_mesh(self.name + "_mesh", verts, faces, edges)
        for mat in old_materials:
            mesh.materials.append(mat)
        self.object.data = mesh

    def update_mesh(self, verts: _Vertices, faces: _Faces, edges: _Edges | None = None) -> None:
        """Updates the object's mesh based on lists of vertices, faces, and edges.

        Args:
            verts: Vertex coordinates, each supplied as a tuple, list, or mathutils.Vector of 2 or 3 floats.
            faces: Faces described by sequences of vertex indices.
            edges: Edges described by sequences of vertex indices. Defaults to None.
        """
        if edges is None:
            edges = []
        mesh = self.object.data
        mesh.clear_geometry()
        mesh.from_pydata(verts, edges, faces)
        mesh.update()

    def update_vertices(self, verts: _Vertices) -> None:
        """Updates the vertices of the object's mesh.

        Args:
            verts: Vertex coordinates, each supplied as a tuple, list, or mathutils.Vector of 2 or 3 floats.
        """
        mesh = self.object.data
        assert len(verts) == len(mesh.vertices)
        for i, v in enumerate(verts):
            mesh.vertices[i].co = v

    def update_faces(self, faces: _Faces) -> None:
        """Updates the faces of the object's mesh.

        Args:
            faces: Faces described by sequences of vertex indices.
        """
        raise NotImplementedError("Updating faces is not implemented yet.")

    def create_vertex_hook(self, name: str, vertex_index: int) -> Empty:
        """Create and return a hook for a given vertex in this object's mesh.

        Args:
            name (str): The name of the hook object.
            vertex_index (int): The index of the vertex to hook.

        Returns:
            Empty: The created hook object.
        """
        assert self._has_data(), f"The object {self.name} has no mesh set."
        obj = self.object
        hook = ebpy.add_hook(obj)

        # Create empty. Note: Lazy import to prevent cyclic imports.
        from .points import Empty

        empty = Empty(location=obj.data.vertices[vertex_index].co, parent=self, name=name)

        # Link the hook to the empty.
        hook.object = empty.object
        hook.vertex_indices_set([vertex_index])

        # Add empty as a child and store hook ref.
        self.add_subobject(empty)
        self._hooks.append(hook)

        # Todo - encapsulate hook in Hook class
        return empty

    @property
    def vertices(self):
        """Get the mesh's vertices.

        Returns:
            bpy.types.MeshVertices: The vertices of the mesh."""
        assert self._has_data(), f"The object {self.name} has no mesh set."
        return self.object.data.vertices

    @property
    def faces(self):
        """Get the mesh's faces.

        Returns:
            bpy.types.MeshPolygons: The faces of the mesh."""
        assert self._has_data(), f"The object {self.name} has no mesh set."
        return self.object.data.polygons

    @property
    def edges(self):
        """Get the mesh's edges.

        Returns:
            bpy.types.MeshEdges: The edges of the mesh."""
        assert self._has_data(), f"The object {self.name} has no mesh set."
        return self.object.data.edges

    # Private methods -------------------------------------------------------------------------------------- #

    def _deepcopy_excluded_attrs(self) -> set[str]:
        """Attributes to exclude from deep copying.

        Returns:
            set[str]: A set of attribute names to exclude from deep copying.
        """
        assert len(self._hooks) == 0, "Cannot deepcopy objects with hooks yet."
        return {"_hooks"} | super()._deepcopy_excluded_attrs()
