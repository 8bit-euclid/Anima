from segment import *
from general import *


clear_scene()
set_render_fps(30)

# line_seg = Segment(vert0=(0.0, 0.0), vert1=(5.0, 0.0), width=0.1, bias=0.0, angle_offs0=0,
#                    angle_offs1=0, intro=('00:00', '00:00:500'))

segs = SegmentChain([(0.0, 0.0), (5.0, 0.0), (10.0, 2.0)], width=0.1, bias=0.0, angle_offs0=0,
                    angle_offs1=0)

# Set end frame
set_end_frame(to_frame('00:03'))

save_as("line")
