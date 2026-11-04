"""Reveal strategies: how an object appears as a progress value goes from 0 (hidden) to 1 (fully shown).

A `Reveal` is bound to one object and knows nothing about time. It only maps a progress to the object's visible state, and
that mapping is idempotent and independent of history, so any progress can be applied at any time, in any order.
Time is the business of `anima.animation.action`.

Objects choose their default strategy through `Object.create_reveal()`, which is the extension point for new
primitives:

- `Draw` traces a curve from its start to its end.
- `Fade` changes opacity without changing scale.
- `Scale` changes scale without changing opacity.
- `Together` applies multiple strategies to the same progress, e.g. `Fade` and `Scale` together.
- `Stagger` spreads the progress over several children (see `anima.animation.stagger`).
- `Phase` runs several reveals in explicit windows of the progress, e.g. outline first and then fill.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable, Sequence
from typing import TYPE_CHECKING, NamedTuple

from anima.animation.stagger import Ordering, in_order, stagger_windows, window_progress
from anima.globals.general import Matrix, Vector

if TYPE_CHECKING:
    from anima.primitives.curves import Curve
    from anima.primitives.object import Object


class Reveal(ABC):
    """Maps a progress in [0, 1] to the visible state of the object it is bound to.

    Subclasses implement `_apply`. A reveal that skips the unchanged progress values it already applied keeps a
    large hierarchy cheap to update, but it assumes nothing else touches the state it controls. Call `invalidate`
    after changing that state by hand, or when another reveal has been driving the same object.

    Attributes:
        target: The object being revealed.
    """

    def __init__(self, target: Object) -> None:
        """Bind the reveal to an object.

        Args:
            target: The object to reveal.
        """
        self.target = target
        self._progress: float | None = None

    @property
    def progress(self) -> float | None:
        """The last applied progress, or None if none has been applied since creation or `invalidate`."""
        return self._progress

    def apply(self, progress: float) -> None:
        """Show the target as it is at a progress, doing nothing if that progress is already applied.

        Args:
            progress: The progress from 0 (hidden) to 1 (fully shown). Values outside [0, 1] are clamped.
        """
        progress = max(0.0, min(1.0, progress))
        if progress == self._progress:
            return
        self._apply(progress)
        self._progress = progress

    def invalidate(self) -> None:
        """Forget the applied progress, so that the next `apply` always updates the target."""
        self._progress = None

    @abstractmethod
    def _apply(self, progress: float) -> None:
        """Update the target for a progress in [0, 1], regardless of what was applied before."""


class Draw(Reveal):
    """Reveal a curve by drawing it from its start to its end, as `param_1` goes from 0 to 1.

    The curve's `param_0` is left as it is, so a curve that starts partway along is drawn from there. Endcaps follow
    the end of the curve and, like any curve of zero length, may still be visible at progress 0.
    """

    target: Curve

    def __init__(self, target: Curve) -> None:
        """Bind the reveal to a curve (or a chain or loop of curves).

        Args:
            target: The curve to draw.
        """
        super().__init__(target)

    def _apply(self, progress: float) -> None:
        self.target.set_param_1(progress)


class Fade(Reveal):
    """Reveal an object and its descendants by changing opacity only."""

    def _apply(self, progress: float) -> None:
        self.target.set_opacity(progress)
        if progress > 0.0:
            self.target.unhide()
        else:
            self.target.hide()


class Scale(Reveal):
    """Reveal an object by scaling it from a reduced size to its full size.

    Scaling uses the object's delta transforms, so it does not disturb the object's own location, rotation and scale.
    This strategy does not change opacity or visibility. Combine it with `Fade` in `Together` when both effects are
    desired. If the object's transform changes after applying progress, call `invalidate` so the next `apply`
    recomputes the pivot compensation.
    """

    def __init__(
        self,
        target: Object,
        *,
        from_scale: float = 0.5,
        pivot: Sequence[float] | None = None,
    ) -> None:
        """Bind the reveal to an object.

        Args:
            target: The object to scale.
            from_scale: The scale at progress 0, as a fraction of full size. The scale grows linearly from this
                to 1.
            pivot: The point, in the object's own coordinates, that stays fixed as it grows. Defaults to the origin.

        Raises:
            ValueError: If `from_scale` is not positive.
        """
        if from_scale <= 0.0:
            raise ValueError(f"The starting scale must be positive: {from_scale}.")
        super().__init__(target)
        self.from_scale = from_scale
        self.pivot = Vector(pivot) if pivot is not None else None

    def _apply(self, progress: float) -> None:
        target = self.target
        scale = self.from_scale + (1.0 - self.from_scale) * progress
        bl_object = target.object
        bl_object.delta_scale = (scale, scale, scale)
        if self.pivot is None:
            bl_object.delta_location = (0.0, 0.0, 0.0)
        else:
            # Growing about the pivot moves it unless the object is shifted back by the growth of its offset from the
            # origin, which is the pivot as the object's rotation and scale place it in the parent's frame.
            linear = target.rotation.to_matrix() @ Matrix.Diagonal(target.scale)
            bl_object.delta_location = (1.0 - scale) * (linear @ self.pivot)


class Together(Reveal):
    """Apply multiple reveal strategies to the same progress value.

    Strategies should control distinct aspects of state, such as `Fade` controlling opacity and `Scale` controlling
    transforms. If strategies modify the same state, the later strategy may overwrite the earlier one's result.
    """

    def __init__(self, target: Object, reveals: Iterable[Reveal]) -> None:
        """Bind several reveal strategies to one progress.

        Args:
            target: The composite object represented by this strategy.
            reveals: Strategies to apply in order. Each strategy may target the composite or one of its components.
        """
        super().__init__(target)
        self.reveals = list(reveals)

    def invalidate(self) -> None:
        super().invalidate()
        for reveal in self.reveals:
            reveal.invalidate()

    def _apply(self, progress: float) -> None:
        for reveal in self.reveals:
            reveal.apply(progress)


class Stagger(Reveal):
    """Reveal several objects (by default the target's children) one after another, with overlap.

    The children, their order and their strategies are fixed when the reveal is created.
    """

    def __init__(
        self,
        target: Object,
        *,
        lag_ratio: float = 0.5,
        order: Ordering | None = None,
        children: Iterable[Object] | None = None,
        child_reveal: Callable[[Object], Reveal] | None = None,
    ) -> None:
        """Bind the reveal to an object.

        Args:
            target: The object to reveal.
            lag_ratio: 0 to reveal all children together, 1 to reveal them strictly one after another, and in
                between to start each child that fraction of its own duration after the previous one.
            order: How to order the children (see `anima.animation.stagger`). Defaults to their natural order.
            children: The objects to reveal. Defaults to the children of the target.
            child_reveal: Creates the reveal of a child. Defaults to the child's own `create_reveal()`.

        Raises:
            ValueError: If `lag_ratio` is not in [0, 1] or `order` is not a permutation.
        """
        super().__init__(target)
        objects = list(target.children if children is None else children)
        sequence = (order or in_order)(objects)
        if sorted(sequence) != list(range(len(objects))):
            raise ValueError(f"The order must be a permutation of range({len(objects)}): {sequence}.")

        make_reveal = child_reveal or (lambda child: child.create_reveal())
        windows = stagger_windows(len(objects), lag_ratio)
        self.lag_ratio = lag_ratio
        self.reveals: list[Reveal] = [make_reveal(child) for child in objects]
        self._windows: list[tuple[float, float]] = [(0.0, 1.0)] * len(objects)
        for place, index in enumerate(sequence):
            self._windows[index] = windows[place]

    def invalidate(self) -> None:
        super().invalidate()
        for reveal in self.reveals:
            reveal.invalidate()

    def _apply(self, progress: float) -> None:
        for reveal, (start, stop) in zip(self.reveals, self._windows, strict=True):
            reveal.apply(window_progress(progress, start, stop))


class PhaseWindow(NamedTuple):
    """A reveal strategy and its window within a `Phase` strategy."""

    reveal: Reveal
    start: float
    stop: float


class Phase(Reveal):
    """Run several reveals in explicit windows of the progress, which may overlap.

    For example, a glyph could draw its outline in the first 70% and fade in its fill from 50%.
    """

    def __init__(self, target: Object, phases: Iterable[PhaseWindow | tuple[Reveal, float, float]]) -> None:
        """Bind the reveal to an object.

        Args:
            target: The object to reveal.
            phases: The reveals and the windows (start, stop) of the progress in which they run.

        Raises:
            ValueError: If a window is not within [0, 1] or ends before it starts.
        """
        super().__init__(target)
        self.phases: list[PhaseWindow] = [PhaseWindow(*phase) for phase in phases]
        for phase in self.phases:
            if not 0.0 <= phase.start <= phase.stop <= 1.0:
                raise ValueError(f"A phase window must satisfy 0 <= start <= stop <= 1: {phase[1:]}.")

    def invalidate(self) -> None:
        super().invalidate()
        for phase in self.phases:
            phase.reveal.invalidate()

    def _apply(self, progress: float) -> None:
        for reveal, start, stop in self.phases:
            reveal.apply(window_progress(progress, start, stop))
