from anima.primitives.curves import Curve

from .action import Action


class Construct(Action):
    def __init__(self, obj):
        super().__init__(obj)

    def set_intro(self, interval):
        obj = self.obj

        if isinstance(obj, Curve):
            # keyframe on data.bevel_factor_end for curve objects.
            pass
        else:
            raise Exception(f"Cannot construct objects of type {type(obj)}")

    def set_outro(self, interval):
        pass
