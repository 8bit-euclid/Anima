import bpy
import sys
from pathlib import Path


def configure_python_path():
    """Add the project root and the src directory to the Python path."""
    root_dir = Path(__file__).parent.parent.parent
    src_dir = root_dir/'src'
    sys.path.insert(0, str(root_dir))
    sys.path.insert(0, str(src_dir))


def configure_viewport():
    # Find and activate the 3D viewport
    from anima.diagnostics import logger
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                for region in area.regions:
                    if region.type == 'WINDOW':
                        override = {
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


def main():
    configure_python_path()
    configure_viewport()

    # Cannot import these at the top because the python path must be set first
    from anima.diagnostics import logger
    from anima.globals.general import clear_scene, to_frame, deselect_all, hide_relationship_lines, ebpy
    from tests.visual_tests.test_curves import test_bezier_splines, test_curve_joints, test_dashed_curves
    from tests.visual_tests.test_latex import test_text_to_glyphs

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

    # Reset to first frame and play
    bpy.context.scene.frame_current = 1
    bpy.ops.screen.animation_play()


if __name__ == "__main__":
    main()
