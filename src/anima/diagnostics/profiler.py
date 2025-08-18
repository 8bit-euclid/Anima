import cProfile
import io
import pstats
from pstats import SortKey


class Profiler:
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
        self._profiler = cProfile.Profile()

    def enable(self):
        """Start collecting profiling data."""
        self._profiler.enable()

    def disable(self):
        """Stop collecting profiling data."""
        self._profiler.disable()

    def print_stats(self):
        """Print the collected profiling statistics, sorted by internal time."""
        stream = io.StringIO()
        sortby = SortKey.TIME
        ps = pstats.Stats(self._profiler, stream=stream).sort_stats(sortby)
        ps.print_stats()
        print(stream.getvalue())


# Single instance for global access
profiler = Profiler()
