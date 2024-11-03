from apeiron.primitives.curves import *
from apeiron.primitives.bezier import BezierSpline, BezierCurve
from apeiron.globals.general import *
import apeiron.startup as startup
import numpy as np

startup.driver_callables.copy_startup_files()
startup.blender_startup.register()
clear_scene()
ebpy.set_render_fps(60)

obj = Rectangle(1, 1)
obj.animate()

bspline = BezierSpline([(1, 0), (2, 1), (3, 0)])
bspline.set_resolution(64)
bspline.set_right_handle_type(1, 'ALIGNED')
bspline.set_left_handle_type(1, 'ALIGNED')
bspline.set_right_handle(1, (0, 0.5))
bspline.set_bias(-1)

bcurve = BezierCurve((0, 0), (0.8, 0), width=0.01)
bcurve.set_resolution(64)
bcurve.set_handle_0((0.5, 0.5))
bcurve.set_handle_1((0, 0.5))

pts = []
for theta in np.linspace(0, 2*math.pi, 50):
    pt = (math.cos(theta), math.sin(theta))
    pts.append(pt)

circle = BezierSpline(pts, width=0.008)
circle.set_resolution(5)
circle.set_width(0.05)
circle.set_bias(1)

add_circle()

# Set end frame
ebpy.set_end_frame(to_frame('00:07'))

save_as("main")
