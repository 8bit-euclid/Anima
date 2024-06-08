from general import *

# Function to create a circle
def create_circle(num_verts, radius):
    verts = []
    for i in range(num_verts):
        angle = 2 * math.pi * i / num_verts
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        verts.append((x, y, 0))
    return verts

# Function to create a mesh from vertices
def create_mesh(verts):
    mesh = bpy.data.meshes.new(name="Circle")
    mesh.from_pydata(verts, [], [(i, i+1) for i in range(len(verts)-1)] + [(len(verts)-1, 0)])
    return mesh

clear_scene()

# Create circle vertices
num_verts = 50  # Number of vertices
radius = 2.0    # Radius of the circle
circle_verts = create_circle(num_verts, radius)

# Create the mesh
circle_mesh = create_mesh(circle_verts)

# Create an object with the mesh
circle_object = bpy.data.objects.new("Circle", circle_mesh)

# Link the object to the scene
scene = bpy.context.scene
scene.collection.objects.link(circle_object)

# Animate drawing the circle outline
frame_start = 1
frame_end = 100
for i in range(frame_start, frame_end + 1):
    bpy.context.scene.frame_set(i)
    circle_object.scale.x = i / frame_end
    circle_object.scale.y = i / frame_end
    circle_object.keyframe_insert(data_path="scale", index=0)
    circle_object.keyframe_insert(data_path="scale", index=1)

bpy.context.scene.frame_end = frame_end

# Save the Blender file
blend_file_path = "circle.blend"
bpy.ops.wm.save_mainfile(filepath=blend_file_path)
