# class Point2(Point):
#     def __init__(self, location=(0, 0, 0), parent=None, name='Point2'):
#         super().__init__(location, parent, name)

#     def update(self):
#         t = e['t']
#         self.location = (t, t, 0)

#     def handler(self, scene, depsgraph):
#         self.update()

# p2 = Point2()

# bpy.app.handlers.frame_change_pre.clear()
# bpy.app.handlers.frame_change_pre.append(p2.handler)
