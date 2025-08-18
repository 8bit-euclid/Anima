from anima.globals.general import Vector
from anima.primitives.bezier_spline import BezierSpline
from anima.primitives.curves import DEFAULT_LINE_WIDTH


class BezierCurve(BezierSpline):
    def __init__(
        self,
        point_0: Vector | tuple,
        point_1: Vector | tuple,
        control_pts: list[Vector | tuple] = None,
        width: float = DEFAULT_LINE_WIDTH,
        bias: float = 0.0,
        name: str = "BezierCurve",
        **kwargs,
    ):
        """Initialize a cubic Bezier curve with two points and optional control points.
        Args:
            point_0 (Vector | tuple): The first point of the curve.
            point_1 (Vector | tuple): The second point of the curve.
            control_pts (list[Vector | tuple]): Optional control points for the curve.
            width (float): The width of the curve.
            bias (float): The bias for the curve.
            name (str): The name of the curve.
            **kwargs: Additional keyword arguments for BezierSpline initialization.
        """
        super().__init__(
            spline_points=[point_0, point_1],
            width=width,
            bias=bias,
            name=name,
            **kwargs,
        )
        if control_pts is not None:
            assert (
                len(control_pts) == 2
            ), "Only cubic Bezier curves are currently supported."
            self.set_handle_0(control_pts[0], relative=False)
            self.set_handle_1(control_pts[1], relative=False)

    def set_handle_0(self, position, relative=True):
        """Set the handle position at point 0.
        Args:
            position (Vector | tuple): The new handle position.
            relative (bool): If True, the position is relative to the point's position.
        """
        self.set_right_handle(0, position, relative)
        return self

    def set_handle_1(self, position, relative=True):
        """Set the handle position at point 1.
        Args:
            position (Vector | tuple): The new handle position.
            relative (bool): If True, the position is relative to the point's position.
        """
        self.set_left_handle(1, position, relative)
        return self

    # Property getters/setters ----------------------------------------------------------------------------- #

    @property
    def handle_0(self) -> Vector:
        """Get the curve's handle 0.
        Returns:
            Vector: The handle 0 position relative to the point's position.
        """
        return self._get_handle(side="RIGHT", point_index=0, relative=True)

    @handle_0.setter
    def handle_0(self, position: Vector | tuple):
        """Set the curve's handle 0.
        Args:
            position (Vector | tuple): The new handle 0 position relative to the point's position.
        """
        self.set_handle_0(position)

    @property
    def handle_1(self) -> Vector:
        """Get the curve's handle 1
        Returns:
            Vector: The handle 1 position relative to the point's position.
        """
        return self._get_handle(side="LEFT", point_index=1, relative=True)

    @handle_1.setter
    def handle_1(self, position: Vector | tuple):
        """Set the curve's handle 1.
        Args:
            position (Vector | tuple): The new handle 1 position relative to the point's position.
        """
        self.set_handle_1(position)
