import bpy
from anima.diagnostics import logger
from anima.globals.general import *
from tests.visual_tests.test_curves import test_bezier_splines, test_curve_joints, test_dashed_curves
from tests.visual_tests.test_latex import test_text_to_glyphs


def main():
    # Find and activate the 3D viewport
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                for region in area.regions:
                    if region.type == 'WINDOW':
                        override = {
                            'window': window,
                            'screen': window.screen,
                            'area': area,
                            'region': region,
                            'space_data': area.spaces.active if hasattr(area.spaces, "active") else area.spaces[0]
                        }
                        logger.debug(
                            "Found 3D viewport. Setting context override...")
                        with bpy.context.temp_override(**override):
                            if bpy.ops.view3d.view_axis.poll():
                                bpy.ops.view3d.view_axis(type='TOP')
                                logger.debug(
                                    "Successfully set 3D viewport to top view")
                        break
                break
        else:
            continue
        break

    logger.info("Blender is ready, starting visual tests...")

    clear_scene()
    ebpy.set_render_fps(60)

    end_frame = to_frame('00:06')

    test_text_to_glyphs()

    test_bezier_splines(end_frame)
    test_curve_joints(end_frame)
    test_dashed_curves(end_frame)

    hide_relationship_lines()
    deselect_all()

    # Set end frame
    ebpy.set_end_frame(end_frame + 50)

    # Preset viewpoint
    bpy.context.preferences.view.show_splash = False
    # bpy.ops.view3d.view_axis(type='TOP')

    # Reset to first frame and play
    bpy.context.scene.frame_current = 1
    bpy.ops.screen.animation_play()


# def main():
#     """Main entry point for the script."""
#     # Run the main function with a delay to ensure Blender is fully initialized
#     bpy.app.timers.register(delayed_main, first_interval=1.0)

#     # handlers.load_post.append(delayed_main)


if __name__ == "__main__":
    main()
