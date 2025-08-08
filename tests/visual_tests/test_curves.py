from anima.diagnostics import profiler
from anima.animation.updater import Updater
from anima.primitives.bezier_spline import BezierSpline
from anima.primitives.bezier_curve import BezierCurve
from anima.primitives.chains import CurveChain
from anima.primitives.curves import DEFAULT_LINE_WIDTH
from anima.primitives.dashed_curves import DashedCurve
from anima.primitives.endcaps import ArrowEndcap, PointEndcap, RoundEndcap
from anima.primitives.lines import Segment
from anima.primitives.points import Empty, Point

up = Updater()


def test_bezier_splines(end_frame: int):
    bspline = BezierSpline([(0, 0), (3, 1), (7, -1)])
    # bspline = BezierSpline([(0, 0), (1, 0), (7, 0)])
    # bspline.set_width(THIN)
    # bspline.set_width(NORMAL)
    bspline.set_left_handle(2, (-2.0, 0))

    bcurve = BezierCurve((0, 0.1), (6, 0.1))
    ln = 10
    ht = 3
    bcurve.handle_0 = (ln, ht)
    bcurve.handle_1 = (-ln, ht)

    e = Empty()
    # e.t = 0.0
    e['t'] = 0.0
    e.add_keyframe('t', frame=30, is_custom=True)
    # e.t = 1.0
    e['t'] = 1.0
    e.add_keyframe('t', frame=end_frame, is_custom=True)

    # bcurve.attachment_0 = ArrowEndcap()
    bcurve.attachment_0 = PointEndcap()
    bcurve.attachment_1 = ArrowEndcap()
    # bspline.attachment_0 = ArrowEndcap()
    bspline.attachment_0 = RoundEndcap()
    bspline.attachment_1 = ArrowEndcap()
    # crv.attachment_0 = RoundEndcap()
    # crv.attachment_1 = RoundEndcap()

    seg_t = Segment((0, 0), (0, 0))
    seg_n = Segment((0, 0), (0, 0))

    p1 = Point(name='Point1')
    p2 = Point(name='Point2')
    # p1['u'] = 0.0
    # dr = p1.create_driver('["u"]')
    # dr.add_input_variable('x', e, '["t"]')
    # dr.set_expression('7*x')

    bspline.bias = -1

    def update(scene):
        t1 = e['t']
        t0 = max(0.0, t1 - 0.3)

        bcurve.param_0 = t0
        bcurve.param_1 = t1

        bspline.param_0 = t0
        bspline.param_1 = t1

        p1.location.x = bspline.point(t1).x
        p2.location.x = bcurve.point(t1).x

        # length = 0.4
        # seg_t.spline_point(0).co = pt
        # seg_t.spline_point(1).co = pt + length * crv.tangent(t, True)

        # seg_n.spline_point(0).co = pt
        # seg_n.spline_point(1).co = pt + length * crv.normal(t, True)

    # up.add_input_variable(e, '["t"]')
    up.add_function(update)


def test_curve_joints(end_frame: int):
    c1 = Segment((0.5, -1), (1, 0))
    # c1 = BezierCurve((0, -1), (1, 0))
    # c1.set_handle_0((1, 0))
    # c1.set_handle_1((-0.25, -1))
    offs = 2.0
    radi = 1.0
    c2 = Segment((1, 0), (offs, 0))
    c3 = Segment((offs, 0), (offs, radi))

    # j1 = Joint(c1, c2)
    # j1 = Joint(c1, c2, fillet_factor=0.5, num_subdiv=1)
    # j1 = Joint(c1, c2, num_subdiv=50)
    # j2 = Joint(c2, c3)
    # j2 = Joint(c2, c3, fillet_factor=0.5, num_subdiv=1)
    # j2 = Joint(c2, c3, num_subdiv=50)

    chain = CurveChain([c1, c2, c3])
    chain.width = DEFAULT_LINE_WIDTH * 30

    e = Empty()
    e['t'] = 0.0
    e.add_keyframe('t', frame=30, is_custom=True)
    e['t'] = 1.0
    e.add_keyframe('t', frame=end_frame, is_custom=True)

    # b = 1
    # j1.bias = b
    # c1.bias = b
    # c2.bias = b
    # c3.bias = b
    # j2.bias = b

    p = Point()
    # chain.bias = 1

    pf = profiler

    def update(scene):
        # depsgraph = bpy.context.evaluated_depsgraph_get()
        # e_eval = e.object.evaluated_get(depsgraph)
        # t = e_eval['t']
        t1 = e['t']

        # b = -1 + 2 * t
        # j1.bias = b
        # c1.bias = b
        # c2.bias = b
        # c3.bias = b
        # j2.bias = b

        # w = THIN + 0.02 * t
        # j1.width = w
        # c1.width = w
        # c2.width = w
        # c3.width = w
        # j2.width = w

        # pt0 = c3.spline_point(0).co
        # pt1 = pt0.copy()
        # theta = t * 2 * math.pi
        # fact = 2
        # pt1.x = pt0.x - radi * math.cos(fact * theta)
        # pt1.y = pt0.y + radi * math.sin(fact * theta)
        # c3.spline_point(1).co = pt1
        # j2._update_geometry()

        # j1.param_1 = 0.5
        # j2.param_1 = 0.5
        # j1.param_1 = t
        # j2.param_1 = t

        # w = THIN + 0.2 * t1
        # chain.width = w
        # chain.width = DEFAULT_LINE_WIDTH * 30
        # chain.bias = 2 * t1 - 1

        t0 = max(0.0, t1 - 0.45)
        chain.param_0 = t0
        chain.param_1 = t1
        p.location = chain.point(t1)

    up.add_function(update)


def test_dashed_curves(end_frame: int):
    width = 1.5*DEFAULT_LINE_WIDTH

    # c1 = Segment((0, -1), (0, 0))
    # c2 = Segment((0, 0), (0.5, 0))
    # c3 = Segment((0.5, 0), (0.5, 1))
    # curve1 = CurveChain([c1, c2, c3], width=width)

    curve2 = BezierSpline([(0, -1), (0, 0), (0.5, 0), (0.5, 1)])
    # curve2.translate(-1, 0)

    # dashed1 = DashedCurve(curve1, width=width)
    # dashed2 = DashedCurve(curve2, width=width)
    dashed2 = curve2.make_dashed()

    gap2 = dashed2._gap_len / dashed2._length
    dash2 = dashed2._dash_len / dashed2._length
    gap_offs = gap2 / (dash2 + gap2)
    scal2 = 1 / (dash2 + gap2)

    radi = 1.0
    e = Empty()
    e['t'] = 0.0
    e.add_keyframe('t', frame=30, is_custom=True)
    e['t'] = radi
    e.add_keyframe('t', frame=end_frame, is_custom=True)

    def updater(scene):
        t1 = e['t']
        t0 = max(0, t1 - 0.57)

        # dashed1.offset = t1
        # dashed1.param_0 = t0
        # dashed1.param_1 = t1

        dashed2.offset = gap_offs + scal2 * t1
        dashed2.param_0 = t0
        dashed2.param_1 = t1

    up.add_function(updater)
