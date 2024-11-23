import bpy
from apeiron.primitives.curves import THIN, NORMAL, THICK, DEFAULT_LINE_WIDTH
from apeiron.primitives.points import Point, Empty
from apeiron.primitives.bezier import BezierSpline, BezierCurve
from apeiron.primitives.lines import Segment, Ray, Line
from apeiron.primitives.endcaps import RoundEndcap, PointEndcap, ArrowEndcap
from apeiron.animation.driver import Driver
from apeiron.globals.general import *
import apeiron.startup as startup
from bpy.app.handlers import persistent


def main():
    startup.driver_callables.copy_startup_files()
    startup.blender_startup.register()
    clear_scene()
    ebpy.set_render_fps(60)

    # seg = Segment((1, 1.5), (3, 2), width=0.05)
    # ray = Ray((0.15, 0.15), (-3, 5), width=0.01)
    # line = Line((0.15, 0.15), (5, -1), width=0.02)

    bspline = BezierSpline([(0, 0), (3, 1), (7, -1)])
    # bspline = BezierSpline([(0, 0), (1, 0), (7, 0)])
    bspline.set_resolution(100)
    # bspline.set_width(THIN)
    bspline.set_width(NORMAL)
    bspline.set_left_handle(2, (-2.0, 0))

    bcurve = BezierCurve((0, 1), (6, 1))
    bcurve.set_resolution(100)
    bcurve.set_handle_0((2, 4))
    bcurve.set_handle_1((-2, 4))

    e = Empty()
    e['t'] = 0.0
    e.add_keyframe('["t"]', frame=30)
    e['t'] = 1.0
    e.add_keyframe('["t"]', frame=to_frame('00:06'))

    # crv = bcurve
    crv = bspline

    # crv.set_attachment_0(PointEndcap())
    # crv.set_attachment_1(PointEndcap())
    crv.set_attachment_0(ArrowEndcap())
    crv.set_attachment_1(ArrowEndcap())
    # crv.set_attachment_0(RoundEndcap())
    # crv.set_attachment_1(RoundEndcap())

    seg_t = Segment((0, 0), (0, 0))
    seg_n = Segment((0, 0), (0, 0))

    p2 = Point(name='Point2')
    p2['u'] = 0.0
    dr = p2.create_driver('["u"]')
    dr.add_input_variable('x', e, '["t"]')
    dr.set_expression('7*x')

    def update(scene):
        t = e['t']

        # crv.spline_point(0).co.y = t
        strt = max(0.0, t - 0.3)
        crv.set_start_param(strt)
        crv.set_end_param(t)

        pt = crv.point(t)

        p2.location.x = pt.x

        # length = 0.4
        # seg_t.spline_point(0).co = pt
        # seg_t.spline_point(1).co = pt + length * crv.tangent(t, True)

        # seg_n.spline_point(0).co = pt
        # seg_n.spline_point(1).co = pt + length * crv.normal(t, True)

    bpy.app.handlers.frame_change_pre.clear()
    bpy.app.handlers.frame_change_pre.append(update)

    # bpy.app.handlers.frame_change_post.clear()
    # bpy.app.handlers.frame_change_post.append(update)

    # class Point2(Point):
    #     def __init__(self, location=(0, 0, 0), parent=None, name='Point2'):
    #         super().__init__(location, parent, name)

    #     def update(self):
    #         t = e['t']
    #         self.location = (t, t, 0)

    #     def handler(self, scene, depsgraph):
    #         self.update()

    # p2 = Point2()

    # bpy.app.handlers.frame_change_pre.clear()
    # bpy.app.handlers.frame_change_pre.append(p2.handler)

    # Deselect all objects in the current view layer and clear the active object
    for obj in bpy.context.view_layer.objects:
        obj.select_set(False)
    bpy.context.view_layer.objects.active = None

    # Set end frame
    ebpy.set_end_frame(to_frame('00:07'))

    # Reset to first frame and play
    bpy.context.scene.frame_current = 1
    bpy.ops.screen.animation_play()


if __name__ == "__main__":
    main()
