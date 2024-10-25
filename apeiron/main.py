from apeiron.primitives.curves import *
from apeiron.globals.general import *
import apeiron.startup as startup

startup.driver_callables.copy_startup_files()
startup.blender_startup.register()
clear_scene()
ebpy.set_render_fps(60)

obj = Rectangle(1, 1)
obj.animate()

# Set end frame
ebpy.set_end_frame(to_frame('00:07'))

save_as("main")
