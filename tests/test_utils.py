import pytest


def assert_vector_equal(v1, v2, places=None):
    for i in range(len(v1)):
        if places is not None:
            assert round(
                v1[i] - v2[i], places) == 0, f"{v1} != {v2} at index {i}"
        else:
            assert v1[i] == v2[i], f"{v1} != {v2} at index {i}"


def assert_death(func, *args, **kwargs):
    with pytest.raises(AssertionError):
        func(*args, **kwargs)
