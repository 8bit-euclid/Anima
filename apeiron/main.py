from apeiron.curves import *
from apeiron.globals.general import *
import apeiron.startup as startup


startup.driver_callables.copy_startup_files()
startup.blender_startup.register()

clear_scene()
set_render_fps(60)

#
#
#

# line_seg = Segment(vert0=(0.0, 0.0), vert1=(5.0, 0.0), width=0.1, bias=0.0, angle_offs0=0,
#                    angle_offs1=0, intro=('00:00', '00:02'), outro=('00:04', '00:06'))

# segs = SegmentChain([(0.0, 0.0), (5.0, 0.0), (10.0, 2.0), (15.0, 2.0)], width=0.1, bias=0.0, angle_offs0=0,
#                     angle_offs1=0, intro=('00:00', '00:02'), outro=('00:04', '00:06'))

# elli = Ellipse((0.0, 0.0), 1.0, 1.0, width=0.01, bias=0.0, angle_offs0=0,
#                angle_offs1=0, intro=('00:00', '00:02'), outro=('00:04', '00:06'))

# obj = Circle((0.0, 0.0), 1.0, width=0.01, bias=0.0,
#              intro=('00:00', '00:02'), outro=('00:04', '00:06'))

# segs = SegmentChain([(0.0, 0.0), (5.0, 0.0), (5.0, 6.0)], width=0.1, bias=0.0, angle_offs0=0,
# segs = SegmentChain([(0.0, 0.0), (5.0, 0.0), (10.0, 5.0)], width=0.1, bias=0.0, angle_offs0=0,
#                     angle_offs1=0, intro=('00:00', '00:07'))

#
#
#

obj = Rectangle(1, 1)
obj.animate()

# Set end frame
set_end_frame(to_frame('00:07'))

save_as("main")
