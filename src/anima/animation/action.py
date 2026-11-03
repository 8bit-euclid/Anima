from abc import ABC
from collections import namedtuple

Interval = namedtuple("Interval", ["start", "stop"])


class Action(ABC):
    def __init__(self, obj, interval: Interval):
        self.obj = obj  # of type Object
        self.interval = Interval(*interval)
