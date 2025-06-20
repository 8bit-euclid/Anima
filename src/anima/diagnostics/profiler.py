import cProfile
import pstats
import io
from pstats import SortKey


class Profiler():
    """
    A simple wrapper around Python's cProfile to profile code execution.

    Usage:
        profiler = Profiler()
        profiler.enable()
        # ... code to profile ...
        profiler.disable()
        profiler.print_stats()
    """

    def __init__(self):
        """Initialize the Profiler instance and underlying cProfile.Profile object."""
        self._prof = cProfile.Profile()

    def enable(self):
        """Start collecting profiling data."""
        self._prof.enable()

    def disable(self):
        """Stop collecting profiling data."""
        self._prof.disable()

    def print_stats(self):
        """Print the collected profiling statistics, sorted by internal time."""
        stream = io.StringIO()
        sortby = SortKey.TIME
        ps = pstats.Stats(self._prof, stream=stream).sort_stats(sortby)
        ps.print_stats()
        print(stream.getvalue())
