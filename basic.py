import bpy

# Function to create a triangle mesh


def create_triangle():
    verts = [(0, 0, 0), (1, 0, 0), (0.5, 1, 0)]  # Vertices of the triangle
    edges = []  # Edges (not needed for a simple triangle)
    # Faces, connecting vertices in a counter-clockwise order
    faces = [(0, 1, 2)]
    mesh = bpy.data.meshes.new("TriangleMesh")  # Create a new mesh
    # Load vertices, edges, and faces to the mesh
    mesh.from_pydata(verts, edges, faces)
    mesh.update()
    return mesh


# Remove all existing objects
for obj in bpy.data.objects:
    bpy.data.objects.remove(obj, do_unlink=True)

# Create a new plane object (square)
bpy.ops.mesh.primitive_plane_add(
    size=10, enter_editmode=False, align='WORLD', location=(0, 0, 0))

# Create a triangle
triangle_mesh = create_triangle()
triangle_object = bpy.data.objects.new("Triangle", triangle_mesh)
bpy.context.collection.objects.link(triangle_object)
bpy.data.objects['Triangle'].location.z += 0.01

# # Set up material and texture
# mat = bpy.data.materials.new(name="SquareMaterial")
# tex = bpy.data.textures.new(name="SquareTexture", type='CLOUDS')
# slot = mat.texture_slots.add()
# slot.texture = tex
# bpy.context.object.data.materials.append(mat)

# Set up animation
obj = bpy.data.objects['Triangle']
# obj = bpy.context.object
obj.animation_data_create()
obj.animation_data.action = bpy.data.actions.new(name="SquareAnimation")

# Define keyframes
frames = 20 * bpy.context.scene.render.fps  # 20 seconds at the current FPS
obj.location.x = -5  # Initial position
obj.keyframe_insert(data_path="location", index=0, frame=1)
obj.location.x = 5  # Final position
obj.keyframe_insert(data_path="location", index=0, frame=frames)

# Set end frame
bpy.context.scene.frame_end = frames

# Save the Blender file
blend_file_path = "basic.blend"
bpy.ops.wm.save_mainfile(filepath=blend_file_path)
