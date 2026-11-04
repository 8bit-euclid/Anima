"""Tests for staggered progress windows and item orderings."""

from types import SimpleNamespace

import pytest

from anima.animation.stagger import (
    by_distance,
    by_key,
    in_order,
    local_progress,
    reversed_order,
    shuffled,
    stagger_progress,
    stagger_windows,
    window_progress,
)


def flatten(windows):
    return [edge for window in windows for edge in window]


LAGS = [0.0, 0.1, 0.3, 0.5, 0.75, 1.0]
COUNTS = [1, 2, 3, 7, 40]


class TestWindowProgress:
    def test_linear_within_window(self):
        assert window_progress(0.5, 0.25, 0.75) == pytest.approx(0.5)
        assert window_progress(0.4, 0.2, 0.6) == pytest.approx(0.5)

    def test_clamped_outside_window(self):
        assert window_progress(0.1, 0.25, 0.75) == 0.0
        assert window_progress(0.9, 0.25, 0.75) == 1.0

    def test_exact_at_window_ends(self):
        assert window_progress(0.25, 0.25, 0.75) == 0.0
        assert window_progress(0.75, 0.25, 0.75) == 1.0

    def test_zero_width_window_jumps(self):
        assert window_progress(0.49, 0.5, 0.5) == 0.0
        assert window_progress(0.5, 0.5, 0.5) == 1.0


class TestStaggerWindows:
    def test_no_lag_runs_together(self):
        assert stagger_windows(4, 0.0) == [(0.0, 1.0)] * 4

    def test_full_lag_runs_in_sequence(self):
        windows = stagger_windows(4, 1.0)
        assert flatten(windows) == pytest.approx([0.0, 0.25, 0.25, 0.5, 0.5, 0.75, 0.75, 1.0])

    def test_partial_lag_overlaps(self):
        # Window length 1 / (3 * 0.5 + 1) = 0.4, starts spaced 0.2 apart.
        windows = stagger_windows(4, 0.5)
        assert flatten(windows) == pytest.approx([0.0, 0.4, 0.2, 0.6, 0.4, 0.8, 0.6, 1.0])

    def test_single_item_spans_everything(self):
        assert stagger_windows(1, 0.7) == [(0.0, 1.0)]

    def test_no_items(self):
        assert stagger_windows(0, 0.5) == []

    @pytest.mark.parametrize("count", COUNTS)
    @pytest.mark.parametrize("lag", LAGS)
    def test_span_zero_to_one(self, count, lag):
        windows = stagger_windows(count, lag)
        assert windows[0][0] == 0.0
        assert windows[-1][1] == pytest.approx(1.0)
        assert all(0.0 <= start <= stop <= 1.0 for start, stop in windows)
        assert [w[0] for w in windows] == sorted(w[0] for w in windows)

    @pytest.mark.parametrize("lag", [-0.1, 1.1])
    def test_rejects_invalid_lag(self, lag):
        with pytest.raises(ValueError):
            stagger_windows(3, lag)

    def test_rejects_negative_count(self):
        with pytest.raises(ValueError):
            stagger_windows(-1, 0.5)


class TestStaggerProgress:
    @pytest.mark.parametrize("count", COUNTS)
    @pytest.mark.parametrize("lag", LAGS)
    def test_hidden_at_zero_and_complete_at_one_exactly(self, count, lag):
        assert stagger_progress(0.0, count, lag) == [0.0] * count
        assert stagger_progress(1.0, count, lag) == [1.0] * count

    @pytest.mark.parametrize("lag", LAGS)
    def test_monotonic_in_progress(self, lag):
        previous = [0.0] * 5
        for step in range(101):
            current = stagger_progress(step / 100, 5, lag)
            assert all(c >= p for c, p in zip(current, previous, strict=True))
            previous = current

    def test_sequential_items_finish_one_by_one(self):
        assert stagger_progress(0.5, 4, 1.0) == pytest.approx([1.0, 1.0, 0.0, 0.0])
        assert stagger_progress(0.375, 4, 1.0) == pytest.approx([1.0, 0.5, 0.0, 0.0])

    def test_earlier_items_are_never_behind_later_ones(self):
        values = stagger_progress(0.37, 6, 0.4)
        assert values == sorted(values, reverse=True)

    def test_local_progress_matches(self):
        values = stagger_progress(0.37, 6, 0.4)
        assert [local_progress(0.37, i, 6, 0.4) for i in range(6)] == values

    def test_order_decides_which_item_runs_first(self):
        # The item at index 2 runs first and the item at index 0 last.
        assert stagger_progress(0.5, 3, 1.0, order=[2, 1, 0]) == pytest.approx([0.0, 0.5, 1.0])

    def test_reversed_order_reverses_the_result(self):
        forward = stagger_progress(0.4, 5, 0.6)
        backward = stagger_progress(0.4, 5, 0.6, order=[4, 3, 2, 1, 0])
        assert backward == pytest.approx(forward[::-1])

    @pytest.mark.parametrize("order", [[0, 0, 1], [0, 1], [0, 1, 3]])
    def test_rejects_orders_that_are_not_permutations(self, order):
        with pytest.raises(ValueError):
            stagger_progress(0.5, 3, 0.5, order=order)


class TestOrderings:
    def test_in_order_and_reversed(self):
        assert in_order("abc") == [0, 1, 2]
        assert reversed_order("abc") == [2, 1, 0]
        assert in_order([]) == []

    def test_by_key(self):
        assert by_key(lambda x: x)([3, 1, 2]) == [1, 2, 0]
        assert by_key(lambda x: x, reverse=True)([3, 1, 2]) == [0, 2, 1]

    def test_by_key_keeps_natural_order_for_ties(self):
        assert by_key(lambda x: x // 10)([11, 12, 5, 13, 6]) == [2, 4, 0, 1, 3]
        assert by_key(lambda x: x // 10, reverse=True)([11, 12, 5, 13, 6]) == [0, 1, 3, 2, 4]

    def test_by_distance_uses_location_by_default(self):
        items = [SimpleNamespace(location=(x, 0, 0)) for x in (5, 1, 3)]
        assert by_distance((0, 0, 0))(items) == [1, 2, 0]
        assert by_distance((5, 0, 0))(items) == [0, 2, 1]

    def test_by_distance_with_position_function(self):
        items = [(0, 4), (0, -1), (0, 2)]
        assert by_distance((0, 0), position=lambda item: item)(items) == [1, 2, 0]

    def test_shuffled_is_a_repeatable_permutation(self):
        items = list(range(20))
        first = shuffled(7)(items)
        assert sorted(first) == items
        assert first == shuffled(7)(items)
        assert first != shuffled(8)(items)
        assert first != items

    def test_orderings_feed_stagger_progress(self):
        items = [SimpleNamespace(location=(x, 0, 0)) for x in (5, 1, 3)]
        order = by_distance((0, 0, 0))(items)
        assert stagger_progress(0.5, 3, 1.0, order=order) == pytest.approx([0.0, 1.0, 0.5])
