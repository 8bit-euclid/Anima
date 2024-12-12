import bpy
from apeiron.primitives.curves import THIN, NORMAL, THICK, DEFAULT_LINE_WIDTH
from apeiron.primitives.points import Point, Empty
from apeiron.primitives.bezier import BezierSpline, BezierCurve
from apeiron.primitives.lines import Segment, Ray, Line
from apeiron.primitives.endcaps import RoundEndcap, PointEndcap, ArrowEndcap
from apeiron.primitives.joints import Joint
from apeiron.animation.updater import Updater
from apeiron.globals.general import *
import apeiron.startup as startup

import cProfile
import pstats
import io
from pstats import SortKey

up = Updater()


def test_splines():
    bspline = BezierSpline([(0, 0), (3, 1), (7, -1)])
    # bspline = BezierSpline([(0, 0), (1, 0), (7, 0)])
    # bspline.set_width(THIN)
    # bspline.set_width(NORMAL)
    bspline.set_left_handle(2, (-2.0, 0))

    bcurve = BezierCurve((0, 0.1), (6, 0.1))
    ln = 10
    ht = 3
    bcurve.set_handle_0((ln, ht))
    bcurve.set_handle_1((-ln, ht))

    e = Empty()
    e['t'] = 0.0
    e.add_keyframe('["t"]', frame=30)
    e['t'] = 1.0
    e.add_keyframe('["t"]', frame=to_frame('00:06'))

    # bcurve.set_attachment_0(ArrowEndcap())
    bcurve.set_attachment_0(PointEndcap())
    bcurve.set_attachment_1(ArrowEndcap())
    # bspline.set_attachment_0(ArrowEndcap())
    bspline.set_attachment_0(RoundEndcap())
    bspline.set_attachment_1(ArrowEndcap())
    # crv.set_attachment_0(RoundEndcap())
    # crv.set_attachment_1(RoundEndcap())

    seg_t = Segment((0, 0), (0, 0))
    seg_n = Segment((0, 0), (0, 0))

    p1 = Point(name='Point1')
    p2 = Point(name='Point2')
    # p1['u'] = 0.0
    # dr = p1.create_driver('["u"]')
    # dr.add_input_variable('x', e, '["t"]')
    # dr.set_expression('7*x')

    bspline.set_bias(-1)

    def update(scene):
        t1 = e['t']
        t0 = max(0.0, t1 - 0.3)

        bcurve.set_param_0(t0)
        bcurve.set_param_1(t1)

        bspline.set_param_0(t0)
        bspline.set_param_1(t1)

        p1.location.x = bspline.point(t1).x
        p2.location.x = bcurve.point(t1).x

        # length = 0.4
        # seg_t.spline_point(0).co = pt
        # seg_t.spline_point(1).co = pt + length * crv.tangent(t, True)

        # seg_n.spline_point(0).co = pt
        # seg_n.spline_point(1).co = pt + length * crv.normal(t, True)

    # up.add_input_variable(e, '["t"]')
    up.add_function(update)


def test_joints():
    c1 = BezierCurve((0, -1), (1, 0))
    c1.set_handle_0((1, 0))
    c1.set_handle_1((-0.25, -1))
    # c1 = Segment((1, -1), (1, 0))
    # c2 = Segment((1, 0), (2, 0))
    offs = 1.1
    radi = 0.09
    c2 = Segment((1, 0), (offs, 0))
    c3 = Segment((offs, 0), (offs, radi))

    # j1 = Joint(c1, c2)
    # j1 = Joint(c1, c2, fillet_factor=0.5, num_subdiv=1)
    j1 = Joint(c1, c2, num_subdiv=50)
    # j2 = Joint(c2, c3)
    # j2 = Joint(c2, c3, fillet_factor=0.5, num_subdiv=1)
    j2 = Joint(c2, c3, num_subdiv=50)

    e = Empty()
    e['t'] = 0.0
    e.add_keyframe('["t"]', frame=30)
    e['t'] = 1.0
    e.add_keyframe('["t"]', frame=to_frame('00:06'))

    # b = 1
    # j1.set_bias(b)
    # c1.set_bias(b)
    # c2.set_bias(b)
    # c3.set_bias(b)
    # j2.set_bias(b)

    def update(scene):
        t = e['t']

        # pr = cProfile.Profile()

        # pr.enable()
        # b = -1 + 2 * t
        # j1.set_bias(b)
        # c1.set_bias(b)
        # c2.set_bias(b)
        # c3.set_bias(b)
        # j2.set_bias(b)
        # pr.disable()

        # w = THIN + 0.02 * t
        # j1.set_width(w)
        # c1.set_width(w)
        # c2.set_width(w)
        # c3.set_width(w)
        # j2.set_width(w)

        pt0 = c3.spline_point(0).co
        pt1 = pt0.copy()
        theta = t * 2 * math.pi
        fact = 2
        pt1.x = pt0.x - radi * math.cos(fact * theta)
        pt1.y = pt0.y + radi * math.sin(fact * theta)
        c3.spline_point(1).co = pt1
        j2._update_geometry()

        # s = io.StringIO()
        # sortby = SortKey.TIME
        # ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
        # ps.print_stats()
        # print(s.getvalue())

    up.add_function(update)


def main():
    startup.driver_callables.copy_startup_files()
    startup.blender_startup.register()
    clear_scene()
    ebpy.set_render_fps(60)

    # seg = Segment((1, 1.5), (3, 2), width=0.05)
    # ray = Ray((0.15, 0.15), (-3, 5), width=0.01)
    # line = Line((0.15, 0.15), (5, -1), width=0.02)

    test_splines()
    test_joints()

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

    # Preset viewpoint
    bpy.ops.view3d.view_axis(type='TOP')

    # Reset to first frame and play
    bpy.context.scene.frame_current = 1
    bpy.ops.screen.animation_play()


if __name__ == "__main__":
    main()
