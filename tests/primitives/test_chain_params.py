"""Characterization tests for `CurveChain` parameter propagation (`param_0` / `param_1`)."""

import copy
import random

import pytest

from anima.primitives.chains import CurveChain, CurveLoop
from anima.primitives.lines import Segment
from tests.utils.test_utils import create_rect_path

TOL = 1e-6


def make_chain(create_joints: bool = False) -> CurveChain:
    """Build a 3-segment chain of unit-length segments."""
    curves = [Segment((0, 0), (1, 0)), Segment((1, 0), (1, 1)), Segment((1, 1), (2, 1))]
    return CurveChain(curves, create_joints=create_joints, width=0.1)


def bevel_factors(chain: CurveChain, end_idx: int) -> list[float]:
    """Return the Blender bevel factor of each segment (joints are meshes and have none)."""
    attr = f"bevel_factor_{'end' if end_idx else 'start'}"
    return [getattr(c.object.data, attr) for c in chain.curves]


def child_params(chain: CurveChain, end_idx: int) -> list[float]:
    return [getattr(c, f"_param_{end_idx}") for c in chain._all_entities]


def expected_unit_bevels(param: float, n: int = 3) -> list[float]:
    """Per-segment bevel factors for a joint-free chain of n equal-length segments."""
    return [min(max(param * n - i, 0.0), 1.0) for i in range(n)]


JUMPS = [0.5, 1.0, 0.0, 0.9, 0.2, 1.0, 0.0, 1 / 3, 2 / 3, 0.34, 0.0, 0.66, 0.1]


class TestChainParamPropagation:
    @pytest.mark.parametrize("end_idx", [0, 1])
    def test_arbitrary_jumps_without_joints(self, end_idx):
        """Forward, backward and non-adjacent jumps all give the exact per-curve bevel factors."""
        chain = make_chain()
        for p in JUMPS:
            getattr(chain, f"set_param_{end_idx}")(p)
            assert bevel_factors(chain, end_idx) == pytest.approx(expected_unit_bevels(p), abs=TOL)

    @pytest.mark.parametrize("p", [0.0, 1 / 3, 2 / 3, 1.0])
    def test_curve_boundaries(self, p):
        """Parameters exactly on a curve boundary settle each curve at 0 or 1 (no stale partial values)."""
        chain = make_chain()
        chain.param_1 = 0.9  # Start from a different state so the sweep has work to do.
        chain.param_1 = p
        assert bevel_factors(chain, 1) == pytest.approx(expected_unit_bevels(p), abs=TOL)

    @pytest.mark.parametrize("create_joints", [False, True])
    @pytest.mark.parametrize("end_idx", [0, 1])
    def test_result_is_independent_of_history(self, create_joints, end_idx):
        """Reaching a parameter via any sequence of jumps equals setting it on a fresh chain."""
        rng = random.Random(0)
        chain = make_chain(create_joints)
        chain.debug_on()  # Also exercises validate_param_state() after every change.
        for _ in range(40):
            p = rng.choice([0.0, 1.0, 1 / 3, 2 / 3, rng.random()])
            getattr(chain, f"set_param_{end_idx}")(p)

            fresh = make_chain(create_joints)
            getattr(fresh, f"set_param_{end_idx}")(p)
            assert child_params(chain, end_idx) == pytest.approx(child_params(fresh, end_idx), abs=TOL)
            assert bevel_factors(chain, end_idx) == pytest.approx(bevel_factors(fresh, end_idx), abs=TOL)

    def test_ends_are_independent(self):
        chain = make_chain()
        chain.param_0 = 0.7
        chain.param_1 = 0.9
        assert bevel_factors(chain, 0) == pytest.approx(expected_unit_bevels(0.7), abs=TOL)
        assert bevel_factors(chain, 1) == pytest.approx(expected_unit_bevels(0.9), abs=TOL)

    def test_inverted_params_are_not_validated(self):
        """`param_0 > param_1` is accepted silently; each end is propagated independently."""
        chain = make_chain()
        chain.param_1 = 0.2
        chain.param_0 = 0.8
        assert chain.param_0 > chain.param_1
        assert bevel_factors(chain, 0) == pytest.approx(expected_unit_bevels(0.8), abs=TOL)
        assert bevel_factors(chain, 1) == pytest.approx(expected_unit_bevels(0.2), abs=TOL)

    def test_deepcopy_preserves_state(self):
        chain = make_chain(create_joints=True)
        chain.param_1 = 0.5
        clone = copy.deepcopy(chain)
        clone.validate_param_state()
        assert child_params(clone, 1) == pytest.approx(child_params(chain, 1), abs=TOL)
        clone.param_1 = 0.9  # The clone's sweep bookkeeping must still be consistent.
        clone.validate_param_state()


class TestChainParamStateValidation:
    @pytest.mark.parametrize("create_joints", [False, True])
    def test_valid_after_construction_and_updates(self, create_joints):
        chain = make_chain(create_joints)
        chain.validate_param_state()
        for p in JUMPS:
            chain.param_1 = p
            chain.param_0 = p / 2
            chain.validate_param_state()

    def test_detects_child_modified_directly(self):
        chain = make_chain()
        chain.param_1 = 0.5
        chain.curves[0]._set_param(0, 1)
        with pytest.raises(AssertionError, match="child 0"):
            chain.validate_param_state()

    def test_reapplying_same_param_does_not_repair_state(self):
        """Documents the weakness the validator guards against: no sweep happens if the index is unchanged."""
        chain = make_chain()
        chain.param_1 = 0.5
        chain.curves[0]._set_param(0, 1)
        chain.param_1 = 0.5
        with pytest.raises(AssertionError):
            chain.validate_param_state()

    def test_debug_mode_raises_on_next_change(self):
        chain = make_chain()
        chain.param_1 = 0.5
        chain.curves[0]._set_param(0, 1)
        chain.debug_on()
        with pytest.raises(AssertionError):
            chain.param_1 = 0.6

    def test_validation_is_skipped_without_debug(self):
        chain = make_chain()
        chain.param_1 = 0.5
        chain.curves[0]._set_param(0, 1)
        chain.param_1 = 0.6  # No error: validation only runs in debug mode.

    def test_detects_stale_curve_index(self):
        chain = make_chain()
        chain.param_1 = 0.5
        chain._curve_1_idx = 0
        with pytest.raises(AssertionError, match="stored curve index"):
            chain.validate_param_state()


class TestLoopParamPropagation:
    def test_loop_jumps_are_consistent(self):
        loop = CurveLoop.from_svg_path(create_rect_path(0, 0, 4, 2))
        loop.debug_on()
        rng = random.Random(1)
        for _ in range(30):
            loop.param_1 = rng.choice([0.0, 1.0, 0.25, 0.5, rng.random()])
            loop.param_0 = rng.random() * 0.2
        loop.validate_param_state()
