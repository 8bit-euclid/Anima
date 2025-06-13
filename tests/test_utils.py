import pytest


def assert_vectors_equal(v1: list, v2: list, places: int = None):
    """Assert that two vectors (lists/tuples) are equal element-wise, up to a given decimal place.
    Args:
        v1 (list or tuple): The first vector to compare.
        v2 (list or tuple): The second vector to compare.
        places (int, optional): The number of decimal places to check for equality. If None, checks for exact equality.
    Raises:
        AssertionError: If the vectors are not equal at any index.
    """
    for i in range(len(v1)):
        if places is not None:
            assert round(
                v1[i] - v2[i], places) == 0, f"{v1} != {v2} at index {i}"
        else:
            assert v1[i] == v2[i], f"{v1} != {v2} at index {i}"


def assert_death(func, *args, **kwargs):
    """Assert that calling func(*args, **kwargs) raises an AssertionError.
    Args:
        func (callable): The function to call.
        *args: Positional arguments to pass to the function.
        **kwargs: Keyword arguments to pass to the function.
    Raises:
        AssertionError: If the function does not raise an AssertionError.
    """
    with pytest.raises(AssertionError):
        func(*args, **kwargs)
