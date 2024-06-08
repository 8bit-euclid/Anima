from segment import Segment
from general import *


clear_scene()
set_render_fps(30)

line_seg = Segment(vert0=(0.0, 0.0), vert1=(5.0, 0.0), thickness=0.1, side_bias=0.0, angle_offs0=0, 
                   angle_offs1=0, intro=('00:00', '00:00:500'))

# Set end frame
set_end_frame(to_frame('00:03'))

save_as("line")