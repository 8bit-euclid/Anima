import bpy
from anima.diagnostics import logger


def configure_blender_viewport():
    # Find and activate the 3D viewport
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
