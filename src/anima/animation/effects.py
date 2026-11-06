"""Effects that map progress values to object state.

An `Effect` knows nothing about time or scheduling. It maps progress to an outcome and may be composed with other
effects:

- `Draw` traces a curve from its start to its end.
- `Fade` changes opacity without changing scale.
- `Scale` changes scale without changing opacity.
- `Together` applies multiple effects to the same progress, e.g. `Fade` and `Scale` together.
- `Stagger` spreads the progress over several children (see `anima.animation.stagger`).
- `Phase` runs several effects in explicit windows of the progress, e.g. outline first and then fill.
"""

from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable, Sequence
from datetime import timedelta
from typing import TYPE_CHECKING, NamedTuple

from anima.animation.stagger import Ordering, in_order, stagger_windows, window_progress
from anima.globals.general import Matrix, Vector

if TYPE_CHECKING:
    from anima.primitives.curves import Curve
    from anima.primitives.object import Object


class Effect(ABC):
    """Maps progress and optional elapsed time to changes in state.

    Subclasses implement `_apply`. Unchanged inputs are skipped by default, keeping large compositions cheap to
    update. Call `invalidate` after changing controlled state by hand or when another effect has changed it.

    Attributes:
        target: The object being affected, or None for an effect such as a callback that has no single target.
    """

    def __init__(self, target: Object | None = None) -> None:
        """Bind the effect to an object when it has one.

        Args:
            target: The object affected by this effect.
        """
        self.target = target
        self._last_input: tuple[float, timedelta | None] | None = None

    @property
    def progress(self) -> float | None:
        """The last applied progress, or None if none has been applied since creation or `invalidate`."""
        return None if self._last_input is None else self._last_input[0]

    def apply(self, progress: float, elapsed: timedelta | None = None) -> None:
        """Apply this effect at a progress value and optional elapsed time.

        Args:
            progress: Progress in [0, 1]. Values outside that range are clamped.
            elapsed: Elapsed time since the action started, when supplied by an action.
        """
        progress = max(0.0, min(1.0, progress))
        current_input = self._cache_input(progress, elapsed)
        if current_input == self._last_input:
            return
        self._apply(progress, elapsed)
        self._last_input = current_input

    def invalidate(self) -> None:
        """Forget cached inputs so the next `apply` always updates the target."""
        self._last_input = None

    @abstractmethod
    def _apply(self, progress: float, elapsed: timedelta | None) -> None:
        """Apply the effect independently of previous state."""

    def _cache_input(self, progress: float, elapsed: timedelta | None) -> tuple[float, timedelta | None]:
        """Return the input tuple used to avoid redundant effect applications."""
        return progress, None


class Draw(Effect):
    """Draw a curve from its start to its end as progress goes from 0 to 1.

    The curve's `param_0` is left as it is, so a curve that starts partway along is drawn from there. Endcaps follow
    the end of the curve and, like any curve of zero length, may still be visible at progress 0.
    """

    target: Curve

    def __init__(self, target: Curve) -> None:
        """Bind the effect to a curve (or a chain or loop of curves).

        Args:
            target: The curve to draw.
        """
        super().__init__(target)

    def _apply(self, progress: float, elapsed: timedelta | None) -> None:
        self.target.set_param_1(progress)


class Fade(Effect):
    """Change opacity of an object and its descendants without changing scale."""

    target: Object

    def _apply(self, progress: float, elapsed: timedelta | None) -> None:
        self.target.set_opacity(progress)
        if progress > 0.0:
            self.target.unhide()
        else:
            self.target.hide()


class Scale(Effect):
    """Scale an object from a reduced size to its full size.

    Scaling uses the object's delta transforms, so it does not disturb the object's own location, rotation and scale.
    This effect does not change opacity or visibility. Combine it with `Fade` in `Together` when both effects are
    desired. If the object's transform changes after applying progress, call `invalidate` so the next `apply`
    recomputes the pivot compensation.
    """

    target: Object

    def __init__(
        self,
        target: Object,
        *,
        from_scale: float = 0.5,
        pivot: Sequence[float] | None = None,
    ) -> None:
        """Bind the effect to an object.

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

    def _apply(self, progress: float, elapsed: timedelta | None) -> None:
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


class Together(Effect):
    """Apply multiple effects to the same progress value.

    Effects should control distinct aspects of state, such as `Fade` controlling opacity and `Scale` controlling
    transforms. If effects modify the same state, the later effect may overwrite the earlier one's result.
    """

    target: Object

    def __init__(self, target: Object, effects: Iterable[Effect]) -> None:
        """Bind several effects to one progress value.

        Args:
            target: The composite object represented by this effect.
            effects: Effects to apply in order. Each may target the composite or one of its components.
        """
        super().__init__(target)
        self.effects = list(effects)

    def invalidate(self) -> None:
        super().invalidate()
        for effect in self.effects:
            effect.invalidate()

    def _apply(self, progress: float, elapsed: timedelta | None) -> None:
        for effect in self.effects:
            effect.apply(progress, elapsed)


class Stagger(Effect):
    """Apply child effects to several objects one after another, with overlap.

    The children, their order and their effects are fixed when the effect is created.
    """

    target: Object

    def __init__(
        self,
        target: Object,
        *,
        lag_ratio: float = 0.5,
        order: Ordering | None = None,
        children: Iterable[Object] | None = None,
        child_effect: Callable[[Object], Effect],
    ) -> None:
        """Bind the effect to an object.

        Args:
            target: The object containing the affected children.
            lag_ratio: 0 to apply to all children together, 1 to apply strictly one after another, and in
                between to start each child that fraction of its own duration after the previous one.
            order: How to order the children (see `anima.animation.stagger`). Defaults to their natural order.
            children: The objects to affect. Defaults to the children of the target.
            child_effect: Creates an effect for each child.

        Raises:
            ValueError: If `lag_ratio` is not in [0, 1] or `order` is not a permutation.
        """
        super().__init__(target)
        objects = list(target.children if children is None else children)
        sequence = (order or in_order)(objects)
        if sorted(sequence) != list(range(len(objects))):
            raise ValueError(f"The order must be a permutation of range({len(objects)}): {sequence}.")

        windows = stagger_windows(len(objects), lag_ratio)
        self.lag_ratio = lag_ratio
        self.effects: list[Effect] = [child_effect(child) for child in objects]
        self._windows: list[tuple[float, float]] = [(0.0, 1.0)] * len(objects)
        for place, index in enumerate(sequence):
            self._windows[index] = windows[place]

    def invalidate(self) -> None:
        super().invalidate()
        for effect in self.effects:
            effect.invalidate()

    def _apply(self, progress: float, elapsed: timedelta | None) -> None:
        for effect, (start, stop) in zip(self.effects, self._windows, strict=True):
            effect.apply(window_progress(progress, start, stop), elapsed)


class PhaseWindow(NamedTuple):
    """An effect and its window within a `Phase` effect."""

    effect: Effect
    start: float
    stop: float


class Phase(Effect):
    """Run several effects in explicit windows of the progress, which may overlap.

    For example, a glyph could draw its outline in the first 70% and fade in its fill from 50%.
    """

    target: Object

    def __init__(self, target: Object, phases: Iterable[PhaseWindow | tuple[Effect, float, float]]) -> None:
        """Bind the effect to an object.

        Args:
            target: The object containing the affected phases.
            phases: The effects and the windows (start, stop) of the progress in which they run.

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
            phase.effect.invalidate()

    def _apply(self, progress: float, elapsed: timedelta | None) -> None:
        for effect, start, stop in self.phases:
            effect.apply(window_progress(progress, start, stop), elapsed)


class Callback(Effect):
    """Adapt a progress function into an effect.

    The function may accept `u` (progress), `t` (elapsed time), or both. Callbacks that use `t` are invoked whenever
    elapsed time changes; progress-only callbacks are skipped when progress is unchanged.
    """

    _PARAMETERS = frozenset({"u", "t"})

    def __init__(self, function: Callable[..., object]) -> None:
        """Create an effect that invokes a function with progress and/or elapsed time.

        Args:
            function: Function taking `u`, `t`, or both, matched by parameter name.

        Raises:
            TypeError: If the function has no parameters or uses unsupported parameter kinds or names.
        """
        parameters = inspect.signature(function).parameters
        if not parameters or not all(
            parameter.kind in (parameter.POSITIONAL_OR_KEYWORD, parameter.KEYWORD_ONLY) and key in self._PARAMETERS
            for key, parameter in parameters.items()
        ):
            raise TypeError(
                f"A callback may only take the parameters 'u' (progress) and 't' (elapsed time): {parameters}."
            )
        super().__init__()
        self.function = function
        self._parameters = tuple(parameters)

    def _cache_input(self, progress: float, elapsed: timedelta | None) -> tuple[float, timedelta | None]:
        if "t" in self._parameters:
            return progress, elapsed
        return progress, None

    def _apply(self, progress: float, elapsed: timedelta | None) -> None:
        values = {"u": progress, "t": elapsed or timedelta(0)}
        self.function(**{key: values[key] for key in self._parameters})
