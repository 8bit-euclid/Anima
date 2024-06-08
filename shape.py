import bpy

# Clear existing objects
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.object.select_by_type(type='MESH')
bpy.ops.object.delete()

# Define vertices of the polygon
vertices = [(0, 0, 0), (2, 0, 0), (2, 2, 0), (0, 2, 0),
            (0, 0, 0)]  # Adjust these coordinates as needed

# Create new mesh
mesh = bpy.data.meshes.new("Polygon")
obj = bpy.data.objects.new("Polygon", mesh)
bpy.context.collection.objects.link(obj)

# Create the mesh
edges = [(i, i+1) for i in range(len(vertices)-1)]
mesh.from_pydata(vertices, edges, [])
mesh.update()

# Set keyframes for animation
for i in range(len(vertices)-1):
    obj.location = vertices[i]
    obj.keyframe_insert(data_path="location", frame=i*10+1)
    obj.location = vertices[i+1]
    obj.keyframe_insert(data_path="location", frame=(i+1)*10)

# Set animation range
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = len(vertices)*10

# Save the Blender file
blend_file_path = "shape.blend"
bpy.ops.wm.save_mainfile(filepath=blend_file_path)
