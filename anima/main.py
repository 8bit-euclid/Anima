import bpy

from anima.globals.general import *
from anima.tests.test_curves import test_bezier_splines, test_curve_joints, test_dashed_curves


def main():
    clear_scene()
    # ebpy.set_render_fps(30)
    # ebpy.set_render_fps(35)
    # ebpy.set_render_fps(40)
    ebpy.set_render_fps(60)

    end_frame = to_frame('00:10')

    test_bezier_splines(end_frame)
    test_curve_joints(end_frame)
    test_dashed_curves(end_frame)

    deselect_all()

    # Set end frame
    ebpy.set_end_frame(end_frame + 50)

    # Preset viewpoint
    bpy.ops.view3d.view_axis(type='TOP')

    # Reset to first frame and play
    bpy.context.scene.frame_current = 1
    bpy.ops.screen.animation_play()


if __name__ == "__main__":
    main()
