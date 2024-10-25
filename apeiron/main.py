from apeiron.primitives.curves import *
from apeiron.globals.general import *
import apeiron.startup as startup
from apeiron.primitives.base import BaseObject, get_blender_object
from apeiron.primitives.points import Empty, Point

startup.driver_callables.copy_startup_files()
startup.blender_startup.register()
clear_scene()
set_render_fps(60)

obj = Rectangle(1, 1)
obj.animate()

# Set end frame
set_end_frame(to_frame('00:07'))

save_as("main")
