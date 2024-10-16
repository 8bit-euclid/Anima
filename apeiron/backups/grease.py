# # Create a new Grease Pencil object
# bpy.ops.object.gpencil_add(location=(0, 0, 0))
# gp_object = bpy.context.object
# gp_object.name = "Animated Line"

# # Switch to Draw Mode
# bpy.ops.object.mode_set(mode='PAINT_GPENCIL')

# # Get the grease pencil data
# gp_data = gp_object.data

# # Create a new layer
# gp_layer = gp_data.layers.new("LineLayer", set_active=True)

# # Create a new frame at frame 1
# gp_frame = gp_layer.frames.new(1)

# # Create a stroke in the frame
# gp_stroke = gp_frame.strokes.new()

# # Set stroke properties (line thickness, material, etc.)
# gp_stroke.display_mode = '3DSPACE'  # Keep the stroke in 3D space
# gp_stroke.points.add(count=3)       # Add two points for a straight line

# # Define the stroke points (start and end of the line)
# gp_stroke.points[0].co = (0, 0, 0)
# gp_stroke.points[1].co = (1, 0, 0)
# gp_stroke.points[2].co = (1, 1, 0)

# # Set the line thickness
# # Set thickness here (default is 1, adjust as needed)
# gp_stroke.line_width = 40

# # Set the strength of the stroke at the points (opacity)
# gp_stroke.points[0].pressure = 1.0
# gp_stroke.points[1].pressure = 1.0

# # Set the stroke join style to Miter (sharp corners)
# gp_stroke.line_join = 'MITER'
# # Optionally, set the miter limit to control sharpness
# gp_stroke.miter_limit = 10.0  # Adjust this value as needed

# gp_stroke.use_cyclic = False  # Ensure it's not a cyclic stroke
# gp_stroke.start_cap_mode = 'FLAT'
# gp_stroke.end_cap_mode = 'FLAT'

# # Assign a Grease Pencil material to the stroke
# gp_material = bpy.data.materials.new(name="GPencilMaterial")
# gp_material.use_nodes = True  # Grease Pencil materials use nodes

# # Add the material to the object and assign it to the stroke
# gp_object.data.materials.append(gp_material)

# # # Add keyframes to animate the line being drawn
# # bpy.context.scene.frame_set(1)  # Start at frame 1
# # # Both points are initially at the start point
# # gp_stroke.points[1].co = (0, 0, 0)
# # gp_stroke.points.update()
# # # Insert keyframe for start
# # gp_stroke.keyframe_insert(data_path="points[1].co", frame=1)

# # # At frame 20, move the second point to the end position
# # bpy.context.scene.frame_set(20)
# # gp_stroke.points[1].co = (5, 5, 0)  # Move to the end point
# # gp_stroke.points.update()
# # # Insert keyframe for end
# # gp_stroke.keyframe_insert(data_path="points[1].co", frame=20)

# # Set the end frame for the animation (optional)
# bpy.context.scene.frame_end = 30

# save_as("lines")
