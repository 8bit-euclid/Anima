"""Staggering: how one progress value is spread over several items, each running in its own window.

With a lag ratio of 0 all items run together. With a lag ratio of 1 they run strictly one after another. Values in
between overlap neighbouring items. These are pure functions, independent of any scene.
"""

from __future__ import annotations

import random
from collections.abc import Callable, Sequence
from typing import Any

Ordering = Callable[[Sequence[Any]], list[int]]
"""Maps items to the indices of the items in the order they should run, e.g. [2, 0, 1] runs the third item first."""

Window = tuple[float, float]


def window_progress(progress: float, start: float, stop: float) -> float:
    """Return the progress within a window of the overall progress.

    Args:
        progress: The overall progress in [0, 1].
        start: Where the window begins in the overall progress.
        stop: Where the window ends in the overall progress. A window with `stop == start` jumps from 0 to 1.

    Returns:
        0 up to `start`, 1 from `stop` onwards, and linear in between.
    """
    if progress >= stop:
        return 1.0
    if progress <= start:
        return 0.0
    return (progress - start) / (stop - start)


def stagger_windows(count: int, lag_ratio: float) -> list[Window]:
    """Compute the window of overall progress in which each of `count` items runs.

    The windows have equal length and start at equal spacing, so that the first starts at 0 and the last ends
    at 1. The start of each item is `lag_ratio` times the window length after the start of the previous one.

    Args:
        count: The number of items.
        lag_ratio: 0 for all items together, 1 for strictly one after another, in [0, 1].

    Returns:
        One (start, stop) window per item, in order.

    Raises:
        ValueError: If `count` is negative or `lag_ratio` is outside [0, 1].
    """
    if count < 0:
        raise ValueError(f"The item count cannot be negative: {count}.")
    if not 0.0 <= lag_ratio <= 1.0:
        raise ValueError(f"The lag ratio must be in [0, 1]: {lag_ratio}.")
    if count == 0:
        return []

    length = 1.0 / ((count - 1) * lag_ratio + 1.0)
    return [(i * lag_ratio * length, min(1.0, i * lag_ratio * length + length)) for i in range(count)]


def local_progress(progress: float, index: int, count: int, lag_ratio: float) -> float:
    """Return the progress of one item out of `count` staggered items, for an overall progress."""
    start, stop = stagger_windows(count, lag_ratio)[index]
    return window_progress(progress, start, stop)


def stagger_progress(progress: float, count: int, lag_ratio: float, order: Sequence[int] | None = None) -> list[float]:
    """Return the progress of every item out of `count` staggered items, for an overall progress.

    Args:
        progress: The overall progress in [0, 1].
        count: The number of items.
        lag_ratio: 0 for all items together, 1 for strictly one after another.
        order: The indices of the items in the order they run. Defaults to their natural order.

    Returns:
        The progress of each item, indexed by the item's position (not by its place in `order`).

    Raises:
        ValueError: If `order` is not a permutation of the item indices.
    """
    windows = stagger_windows(count, lag_ratio)
    if order is None:
        return [window_progress(progress, start, stop) for start, stop in windows]
    if sorted(order) != list(range(count)):
        raise ValueError(f"The order must be a permutation of range({count}): {list(order)}.")

    result = [0.0] * count
    for place, index in enumerate(order):
        result[index] = window_progress(progress, *windows[place])
    return result


# Orderings ------------------------------------------------------------------------------------------------- #


def in_order(items: Sequence[Any]) -> list[int]:
    """Run the items in their natural order."""
    return list(range(len(items)))


def reversed_order(items: Sequence[Any]) -> list[int]:
    """Run the items from last to first."""
    return list(reversed(range(len(items))))


def by_key(key: Callable[[Any], float], *, reverse: bool = False) -> Ordering:
    """Create an ordering that runs items by increasing `key`, keeping the natural order for ties.

    Args:
        key: Maps an item to a number.
        reverse: Run by decreasing key instead. Ties still keep their natural order.
    """

    def ordering(items: Sequence[Any]) -> list[int]:
        return sorted(range(len(items)), key=lambda i: key(items[i]), reverse=reverse)

    return ordering


def by_distance(point: Sequence[float], position: Callable[[Any], Sequence[float]] | None = None) -> Ordering:
    """Create an ordering that runs items by increasing distance from a point.

    Args:
        point: The point the reveal spreads out from.
        position: Maps an item to its position. Defaults to the item's `location`.
    """

    def distance(item: Any) -> float:
        pos = position(item) if position is not None else item.location
        return sum((a - b) ** 2 for a, b in zip(pos, point, strict=True))

    return by_key(distance)


def shuffled(seed: int) -> Ordering:
    """Create an ordering that runs items in a random but repeatable order.

    Args:
        seed: The seed of the shuffle. The same seed gives the same order for the same number of items.
    """

    def ordering(items: Sequence[Any]) -> list[int]:
        indices = list(range(len(items)))
        random.Random(seed).shuffle(indices)
        return indices

    return ordering
