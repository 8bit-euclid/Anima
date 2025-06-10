import cProfile
import pstats
import io
from pstats import SortKey


class Profiler():
    def __init__(self):
        self._prof = cProfile.Profile()

    def enable(self):
        self._prof.enable()

    def disable(self):
        self._prof.disable()

    def print_stats(self):
        stream = io.StringIO()
        sortby = SortKey.TIME
        ps = pstats.Stats(self._prof, stream=stream).sort_stats(sortby)
        ps.print_stats()
        print(stream.getvalue())
