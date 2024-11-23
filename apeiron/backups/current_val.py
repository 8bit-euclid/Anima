# def current_value(self, bl_data_path):
#     fcurves = self.bl_obj.animation_data.action.fcurves
#     found = False
#     for fcurve in fcurves:
#         if fcurve.data_path == '["t"]':
#             frame = bpy.context.scene.frame_current
#             value = fcurve.evaluate(frame)
#             found = True
#             break
#     if not found:
#         raise Exception(f'No animation data for path: {bl_data_path}')
#     return value
