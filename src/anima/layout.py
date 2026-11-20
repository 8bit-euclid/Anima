"""One-time, non-owning arrangements of scene objects."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from math import isfinite
from typing import TYPE_CHECKING, Literal, TypeVar

import bpy
from mathutils import Matrix, Vector

from anima.scene.state import get_profile

if TYPE_CHECKING:
    from anima.primitives.object import Object

Direction = Literal["right", "left", "up", "down", "r", "l", "u", "d"] | str
Alignment = Literal["origin", "center", "left", "right", "top", "bottom", "c", "l", "r", "t", "b"] | str
Anchor = (
    Literal[
        "center",
        "left",
        "right",
        "top",
        "bottom",
        "top_left",
        "top_right",
        "bottom_left",
        "bottom_right",
        "c",
        "l",
        "r",
        "t",
        "b",
        "tl",
        "tr",
        "bl",
        "br",
    ]
    | str
)

_CanonicalDirection = Literal["right", "left", "up", "down"]
_CanonicalAlignment = Literal["origin", "center", "left", "right", "top", "bottom"]
_CanonicalAnchor = Literal[
    "center", "left", "right", "top", "bottom", "top_left", "top_right", "bottom_left", "bottom_right"
]
_T = TypeVar("_T", bound=str)

_DIRECTIONS: tuple[_CanonicalDirection, ...] = ("right", "left", "up", "down")
_ANCHORS: tuple[_CanonicalAnchor, ...] = (
    "center",
    "left",
    "right",
    "top",
    "bottom",
    "top_left",
    "top_right",
    "bottom_left",
    "bottom_right",
)
_SHORT_NAMES = {
    "r": "right",
    "l": "left",
    "u": "up",
    "d": "down",
    "c": "center",
    "t": "top",
    "b": "bottom",
    "tl": "top_left",
    "tr": "top_right",
    "bl": "bottom_left",
    "br": "bottom_right",
}


def _normalize(value: str, choices: Sequence[_T], kind: str) -> _T:
    if isinstance(value, str):
        normalized = value.lower()
        normalized = _SHORT_NAMES.get(normalized, normalized)
        for choice in choices:
            if normalized == choice:
                return choice
    raise ValueError(f"Invalid {kind}: {value!r}.")


@dataclass(frozen=True)
class _Bounds:
    left: float
    bottom: float
    right: float
    top: float

    def moved(self, x: float, y: float) -> _Bounds:
        return _Bounds(self.left + x, self.bottom + y, self.right + x, self.top + y)

    def anchor(self, anchor: Anchor) -> tuple[float, float]:
        anchor = _normalize(anchor, _ANCHORS, "anchor")
        x = (
            self.left
            if anchor in ("left", "top_left", "bottom_left")
            else (self.right if anchor in ("right", "top_right", "bottom_right") else (self.left + self.right) / 2)
        )
        y = (
            self.top
            if anchor in ("top", "top_left", "top_right")
            else (self.bottom if anchor in ("bottom", "bottom_left", "bottom_right") else (self.bottom + self.top) / 2)
        )
        return x, y


@dataclass
class _Arrangement:
    bounds: _Bounds
    positions: list[tuple[Object, float, float]]

    def moved(self, x: float, y: float) -> _Arrangement:
        return _Arrangement(self.bounds.moved(x, y), [(obj, px + x, py + y) for obj, px, py in self.positions])


def _combine(arrangements: Sequence[_Arrangement]) -> _Arrangement:
    return _Arrangement(
        _Bounds(
            min(item.bounds.left for item in arrangements),
            min(item.bounds.bottom for item in arrangements),
            max(item.bounds.right for item in arrangements),
            max(item.bounds.top for item in arrangements),
        ),
        [position for item in arrangements for position in item.positions],
    )


def _object_bounds(obj: Object) -> _Bounds:
    points: list[Vector] = []

    def visit(current: Object, matrix: Matrix) -> None:
        bl_object = current.object
        if bl_object.constraints or bl_object.modifiers:
            raise ValueError(f"Cannot measure {current.name!r}: constraints and modifiers are not supported.")
        if bl_object.parent is not (current.parent.object if current.parent is not None else None):
            raise ValueError(f"Cannot measure {current.name!r}: Blender and Anima parents differ.")
        if bl_object.type == "MESH":
            has_geometry = bool(bl_object.data.vertices)
        elif bl_object.type == "CURVE":
            has_geometry = bool(bl_object.data.splines)
        elif bl_object.type == "EMPTY":
            has_geometry = False
        else:
            raise ValueError(f"Cannot measure {current.name!r}: unsupported object type {bl_object.type!r}.")
        if has_geometry:
            points.extend(matrix @ Vector(corner) for corner in bl_object.bound_box)
        for child in current.children:
            visit(child, matrix @ child.object.matrix_local)

    visit(obj, obj.object.matrix_local)
    if not points:
        raise ValueError(f"Cannot measure {obj.name!r}: it has no geometry.")
    if not all(isfinite(coordinate) for point in points for coordinate in point):
        raise ValueError(f"Cannot measure {obj.name!r}: its bounds are not finite.")
    return _Bounds(
        min(point.x for point in points),
        min(point.y for point in points),
        max(point.x for point in points),
        max(point.y for point in points),
    )


def _validate_objects(objects: Sequence[Object]) -> None:
    if not objects:
        raise ValueError("A layout must contain at least one object.")
    if len({id(obj) for obj in objects}) != len(objects):
        raise ValueError("An object cannot appear more than once in a layout.")
    if any(obj.parent is not objects[0].parent for obj in objects):
        raise ValueError("Layout objects must share the same parent.")
    if any(obj.parent is not None and obj.object.matrix_parent_inverse != Matrix.Identity(4) for obj in objects):
        raise ValueError("Layout objects with a non-identity parent inverse are not supported.")


def _normalize_alignment(align: Alignment, axis: Literal["x", "y"]) -> _CanonicalAlignment:
    choices: tuple[_CanonicalAlignment, ...] = (
        ("origin", "center", "left", "right") if axis == "x" else ("origin", "center", "top", "bottom")
    )
    return _normalize(align, choices, f"{axis}-axis alignment")


def _aligned_coordinate(bounds: _Bounds, align: _CanonicalAlignment, axis: Literal["x", "y"]) -> float:
    if align == "origin":
        return 0.0
    if axis == "x":
        return (
            bounds.left if align == "left" else bounds.right if align == "right" else (bounds.left + bounds.right) / 2
        )
    return bounds.top if align == "top" else bounds.bottom if align == "bottom" else (bounds.top + bounds.bottom) / 2


def _place_next_to(obj: Object, reference: Object, direction: Direction, gap: float, align: Alignment) -> None:
    from anima.primitives.object import Object

    if not isinstance(reference, Object):
        raise TypeError("reference must be an Object.")
    direction = _normalize(direction, _DIRECTIONS, "direction")
    _validate_gap(gap)
    horizontal = direction in ("right", "left")
    axis = "y" if horizontal else "x"
    align = _normalize_alignment(align, axis)
    _validate_objects((obj, reference))
    bpy.context.view_layer.update()
    obj_bounds = _object_bounds(obj).moved(-obj.location.x, -obj.location.y)
    ref_bounds = _object_bounds(reference).moved(-reference.location.x, -reference.location.y)
    if horizontal:
        x = reference.location.x + (
            ref_bounds.right + gap - obj_bounds.left
            if direction == "right"
            else ref_bounds.left - gap - obj_bounds.right
        )
        y = (
            reference.location.y
            + _aligned_coordinate(ref_bounds, align, axis)
            - _aligned_coordinate(obj_bounds, align, axis)
        )
    else:
        x = (
            reference.location.x
            + _aligned_coordinate(ref_bounds, align, axis)
            - _aligned_coordinate(obj_bounds, align, axis)
        )
        y = reference.location.y + (
            ref_bounds.top + gap - obj_bounds.bottom if direction == "up" else ref_bounds.bottom - gap - obj_bounds.top
        )
    obj.set_location(x=x, y=y)


class Layout:
    """Arrange existing objects without adopting them or changing their hierarchy.

    Layouts are descriptions: call ``place`` or ``place_in_safe_area`` to
    calculate and apply positions. Calling either again recalculates the layout.
    Bounds include hidden geometry and are measured in the shared parent frame.
    """

    def __init__(self, items: Iterable[Object | Layout]) -> None:
        """Create a layout from objects or nested layouts."""
        self._items = tuple(items)
        self._rows: tuple[tuple[Object | Layout, ...], ...] | None = None
        self._direction: _CanonicalDirection = "down"
        self._alignment: _CanonicalAlignment = "origin"
        self._align_x: _CanonicalAlignment = "left"
        self._align_y: _CanonicalAlignment = "origin"
        self._gap = 0.5
        self._column_gap = 0.5
        self._row_gap = 0.5

    def tile(self, *, direction: Direction = "down", gap: float = 0.5, align: Alignment = "origin") -> Layout:
        """Arrange items in a row or column when the layout is placed.

        Args:
            direction: Direction in which successive items are placed.
            gap: Distance between bounding boxes, in scene units.
            align: Align origins, centers, or the appropriate edges on the cross axis.

        Returns:
            This layout.

        Raises:
            ValueError: If the direction, alignment, or gap is invalid.
        """
        normalized_direction = _normalize(direction, _DIRECTIONS, "direction")
        normalized_align = _normalize_alignment(align, "y" if normalized_direction in ("left", "right") else "x")
        _validate_gap(gap)
        self._direction, self._gap, self._alignment = normalized_direction, gap, normalized_align
        self._rows = None
        return self

    @classmethod
    def grid(
        cls,
        rows: Iterable[Iterable[Object | Layout]],
        *,
        column_gap: float = 0.5,
        row_gap: float = 0.5,
        align_x: Alignment = "left",
        align_y: Alignment = "origin",
    ) -> Layout:
        """Create a grid with content-sized columns and top-to-bottom rows.

        Rows may contain different numbers of cells.

        Args:
            rows: Rows of objects or nested layouts.
            column_gap: Horizontal gap between columns, in scene units.
            row_gap: Vertical gap between rows, in scene units.
            align_x: Horizontal alignment within each column.
            align_y: Vertical alignment within each row.

        Raises:
            ValueError: If rows are empty or the alignment or gaps are invalid.
        """
        _validate_gap(column_gap)
        _validate_gap(row_gap)
        normalized_x = _normalize_alignment(align_x, "x")
        normalized_y = _normalize_alignment(align_y, "y")
        grid_rows = tuple(tuple(row) for row in rows)
        if not grid_rows or any(not row for row in grid_rows):
            raise ValueError("A grid must contain nonempty rows.")
        layout = cls(item for row in grid_rows for item in row)
        layout._rows = grid_rows
        layout._column_gap, layout._row_gap = column_gap, row_gap
        layout._align_x, layout._align_y = normalized_x, normalized_y
        return layout

    def place(
        self,
        *,
        at: tuple[float, float] = (0.0, 0.0),
        bounds: tuple[float, float, float, float] | None = None,
        anchor: Anchor = "top_left",
    ) -> Layout:
        """Place a layout anchor at ``at`` in its shared parent frame.

        Args:
            at: Anchor position in scene units.
            bounds: Optional allowed rectangle as (left, bottom, right, top).
            anchor: Point on the layout's measured bounds.

        Returns:
            This layout.

        Raises:
            ValueError: If geometry, ownership, arguments, or the available area
                cannot support the arrangement. No objects are moved on failure.
            TypeError: If an item is not an Object or a Layout.
        """
        if len(at) != 2 or not all(isfinite(value) for value in at):
            raise ValueError("at must contain two finite coordinates.")
        if bounds is not None:
            if len(bounds) != 4 or not all(isfinite(value) for value in bounds):
                raise ValueError("bounds must contain four finite coordinates.")
            left, bottom, right, top = bounds
            if left > right or bottom > top:
                raise ValueError("bounds must have nonnegative width and height.")
        _validate_objects(self._objects())
        bpy.context.view_layer.update()
        arrangement = self._arrange()
        x, y = arrangement.bounds.anchor(anchor)
        arrangement = arrangement.moved(at[0] - x, at[1] - y)
        box = arrangement.bounds
        if bounds is not None and (
            box.left < left - 1e-6 or box.bottom < bottom - 1e-6 or box.right > right + 1e-6 or box.top > top + 1e-6
        ):
            raise ValueError("The layout exceeds the available bounds.")
        for obj, x, y in arrangement.positions:
            obj.set_location(x=x, y=y)
        return self

    def place_in_safe_area(self, *, anchor: Anchor = "top_left") -> Layout:
        """Place a root-level layout at the corresponding safe-area anchor.

        Args:
            anchor: Point on the layout and the safe-area rectangle to align.

        Returns:
            This layout.

        Raises:
            ValueError: If any object has a parent or the layout exceeds the safe area.
        """
        if any(obj.parent is not None for obj in self._objects()):
            raise ValueError("Safe-area placement requires root-level objects.")
        width, height = get_profile().safe_size
        safe = _Bounds(-width / 2, -height / 2, width / 2, height / 2)
        return self.place(at=safe.anchor(anchor), bounds=(safe.left, safe.bottom, safe.right, safe.top), anchor=anchor)

    def _objects(self) -> list[Object]:
        from anima.primitives.object import Object

        objects: list[Object] = []
        for item in self._items:
            if isinstance(item, Layout):
                objects.extend(item._objects())
            elif isinstance(item, Object):
                objects.append(item)
            else:
                raise TypeError("Layout items must be Objects or Layouts.")
        return objects

    def _arrange(self) -> _Arrangement:
        if not self._items:
            raise ValueError("A layout must contain at least one item.")
        if self._rows is not None:
            rows = [[self._measure(item) for item in row] for row in self._rows]
            return _arrange_grid(rows, self._column_gap, self._row_gap, self._align_x, self._align_y)
        items = [self._measure(item) for item in self._items]
        if self._direction in ("left", "up"):
            items.reverse()
        if self._direction in ("left", "right"):
            top = max(item.bounds.top - _aligned_coordinate(item.bounds, self._alignment, "y") for item in items)
            return _arrange_grid([items], self._gap, 0, "left", self._alignment).moved(0, top)
        left = min(item.bounds.left - _aligned_coordinate(item.bounds, self._alignment, "x") for item in items)
        return _arrange_grid([[item] for item in items], 0, self._gap, self._alignment, "top").moved(left, 0)

    @staticmethod
    def _measure(item: Object | Layout) -> _Arrangement:
        if isinstance(item, Layout):
            return item._arrange()
        bounds = _object_bounds(item)
        return _Arrangement(bounds.moved(-item.location.x, -item.location.y), [(item, 0.0, 0.0)])


def _validate_gap(gap: float) -> None:
    if not isfinite(gap) or gap < 0:
        raise ValueError("Layout gaps must be finite and non-negative.")


def _arrange_grid(
    rows: list[list[_Arrangement]],
    column_gap: float,
    row_gap: float,
    align_x: _CanonicalAlignment,
    align_y: _CanonicalAlignment,
) -> _Arrangement:
    columns = [[row[i] for row in rows if i < len(row)] for i in range(max(map(len, rows)))]
    x_offsets = [
        (
            min(item.bounds.left - _aligned_coordinate(item.bounds, align_x, "x") for item in column),
            max(item.bounds.right - _aligned_coordinate(item.bounds, align_x, "x") for item in column),
        )
        for column in columns
    ]
    x_positions = []
    x = 0.0
    for left, right in x_offsets:
        x_positions.append(x - left)
        x += right - left + column_gap
    placed = []
    y = 0.0
    for row in rows:
        top = max(item.bounds.top - _aligned_coordinate(item.bounds, align_y, "y") for item in row)
        bottom = min(item.bounds.bottom - _aligned_coordinate(item.bounds, align_y, "y") for item in row)
        for x, item in zip(x_positions, row, strict=False):
            placed.append(
                item.moved(
                    x - _aligned_coordinate(item.bounds, align_x, "x"),
                    y - top - _aligned_coordinate(item.bounds, align_y, "y"),
                )
            )
        y -= top - bottom + row_gap
    return _combine(placed)
