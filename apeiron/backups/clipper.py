# def _update_geometry(self):
#    #
#    self.make_active()
#    extrude_active_obj((0, 0, SMALL_OFFSET))
#    self.make_inactive()
#    #

# def _update_clipper(self, position):
#     if self._clipper is None:
#         w = self._width
#         hw = 0.5 * w
#         obj = add_cuboid(length=3*w, width=w, height=hw)
#         self._clipper = CustomObject(obj)

#         # Tranlate along y so that bottom face is coincident with the origin.
#         clipper = self._clipper
#         clipper.translate(y=hw, local=True, apply=True)

#         # Add a boolean modifier to the clipper
#         mod = self.object.modifiers.new(name="Boolean", type='BOOLEAN')
#         mod.operation = 'DIFFERENCE'  # This will subtract the clipper
#         mod.object = clipper.object

#     # Update clipper
#     self._clipper.location = position
#     # self.update_param_0()
#     self.update_param_1()


# def _set_param(self, param: float, end_index: int):
#     #

#     x_axis = self.point(param) - self._vertices[0]
#     assert math.isclose(UnitZ.dot(x_axis),
#                         0), "Currently only works in 2D."
#     y_axis = UnitZ.cross(x_axis)

#     self._clipper.set_orientation(x_axis, y_axis)

#     #
