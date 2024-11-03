from abc import abstractmethod
from .curve import BaseCurve


class Join(BaseCurve):
    pass

# Note that 'None' is used for a none-type join


class Miter(Join):
    pass


class Bevel(Join):
    pass


class Round(Join):
    pass
