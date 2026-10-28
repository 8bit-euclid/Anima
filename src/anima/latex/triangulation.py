"""Interchangeable polygon triangulators for glyph bodies.

Each triangulator turns one outer boundary plus its holes into triangles over exactly the given points (no Steiner
points are added). Backends are registered by name so that they can be compared.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence

import numpy as np

Ring = np.ndarray  # (N, 2) float array of polygon vertices


class Triangulator(ABC):
    """Triangulates a polygon with holes without adding any vertices."""

    name: str

    def triangulate(self, outer: Ring, holes: Sequence[Ring] = ()) -> np.ndarray:
        """Triangulate a polygon with holes.

        Args:
            outer: (N, 2) outer boundary vertices.
            holes: (K, 2) vertex arrays of the holes, which must lie inside the outer boundary.

        Returns:
            An (M, 3) integer array of counter-clockwise triangles indexing the concatenation of `outer`
            followed by each hole, in order.
        """
        rings = [np.asarray(outer, dtype=np.float64), *(np.asarray(h, dtype=np.float64) for h in holes)]
        faces = np.asarray(self._triangulate(rings), dtype=np.int64).reshape(-1, 3)
        if len(faces) == 0:
            return faces

        # Normalise the winding so that every face normal points along +z.
        pts = np.concatenate(rings)
        a, b, c = pts[faces[:, 0]], pts[faces[:, 1]], pts[faces[:, 2]]
        cross = (b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0])
        faces[cross < 0] = faces[cross < 0][:, ::-1]
        return faces

    @abstractmethod
    def _triangulate(self, rings: list[Ring]) -> np.ndarray:
        """Return triangle indices into the concatenation of `rings` (outer ring first, then holes)."""


class EarcutTriangulator(Triangulator):
    """Ear clipping via the `mapbox-earcut` package."""

    name = "earcut"

    def _triangulate(self, rings: list[Ring]) -> np.ndarray:
        import mapbox_earcut

        pts = np.ascontiguousarray(np.concatenate(rings))
        ends = np.cumsum([len(r) for r in rings]).astype(np.uint32)
        return mapbox_earcut.triangulate_float64(pts, ends)


class BlenderTriangulator(Triangulator):
    """Blender's built-in `mathutils.geometry.tessellate_polygon`."""

    name = "blender"

    def _triangulate(self, rings: list[Ring]) -> np.ndarray:
        import bpy  # noqa: F401  mathutils must be imported after bpy outside of Blender
        from mathutils import Vector
        from mathutils.geometry import tessellate_polygon

        polylines = [[Vector((x, y, 0.0)) for x, y in ring] for ring in rings]
        return np.array(tessellate_polygon(polylines), dtype=np.int64)


_TRIANGULATORS: dict[str, type[Triangulator]] = {cls.name: cls for cls in (EarcutTriangulator, BlenderTriangulator)}
DEFAULT_TRIANGULATOR = EarcutTriangulator.name


def get_triangulator(name: str = DEFAULT_TRIANGULATOR) -> Triangulator:
    """Create a registered triangulator.

    Args:
        name: Registered backend name ("earcut" or "blender").

    Raises:
        ValueError: If `name` is not a registered backend.
    """
    try:
        return _TRIANGULATORS[name]()
    except KeyError:
        raise ValueError(f"Unknown triangulator '{name}'. Available: {sorted(_TRIANGULATORS)}") from None


def available_triangulators() -> list[str]:
    """Return the names of all registered triangulators."""
    return sorted(_TRIANGULATORS)
