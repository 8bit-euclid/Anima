import bpy

# Create the triangle
vertices = [(0, 2, 0), (-2, -2, 0), (2, -2, 0)]
faces = [(0, 1, 2)]

mesh = bpy.data.meshes.new(name="Triangle")
mesh.from_pydata(vertices, [], faces)
mesh.update()

obj = bpy.data.objects.new(name="Triangle_Object", object_data=mesh)
bpy.context.collection.objects.link(obj)

# Create a plane (or any other 2D object)
bpy.ops.mesh.primitive_plane_add(size=1, location=(0.0, 0.0, -0.1))
# bpy.ops.mesh.primitive_cube_add(size=1)
plane = bpy.context.active_object

# Enter edit mode to extrude the plane
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate={"value": (0, 0, 0.2)})
bpy.ops.object.mode_set(mode="OBJECT")

plane.hide_viewport = True

# Add a boolean modifier to the triangle object
bool_mod = obj.modifiers.new(name="Boolean", type="BOOLEAN")
bool_mod.operation = "DIFFERENCE"  # This will subtract the plane
bool_mod.object = plane

plane.location.x = 0.0
plane.keyframe_insert(data_path="location", index=0, frame=0)
plane.location.x = 1.0
plane.keyframe_insert(data_path="location", index=0, frame=400)

# Apply the modifier (optional, if you want to make the effect permanent)
bpy.ops.object.modifier_apply(modifier="Boolean")
