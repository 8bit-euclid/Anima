import bpy

# sample data
coords = [(0, 0, 0), (1, 0, 0), (1, 1, 0)]

# create the Curve Datablock
curveData = bpy.data.curves.new('myCurve', type='CURVE')
curveData.dimensions = '2D'
curveData.resolution_u = 20
curveData.bevel_resolution = 40
curveData.bevel_depth = 0.0

# map coords to spline
polyline = curveData.splines.new('POLY')
polyline.points.add(len(coords))
for i, coord in enumerate(coords):
    x, y, z = coord
    polyline.points[i].co = (x, y, z, 1)

# create Object
curveOB = bpy.data.objects.new('myCurve', curveData)

# attach to scene and validate context
scn = bpy.context.scene
scn.collection.objects.link(curveOB)
bpy.context.view_layer.objects.active = curveOB

# Save the Blender file
blend_file_path = "curve.blend"
bpy.ops.wm.save_mainfile(filepath=blend_file_path)
