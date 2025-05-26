import bpy

from anima.globals.general import *
from tests.visual_tests.test_curves import test_bezier_splines, test_curve_joints, test_dashed_curves
from tests.visual_tests.test_latex import test_text_to_glyphs


def main():
    clear_scene()
    ebpy.set_render_fps(60)

    end_frame = to_frame('00:10')

    test_text_to_glyphs()

    test_bezier_splines(end_frame)
    test_curve_joints(end_frame)
    test_dashed_curves(end_frame)

    hide_relationship_lines()
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
