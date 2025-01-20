# def create_poly_spline(name: str, points):
#     assert len(points) > 1, 'A poly spline must contain at least 2 points.'

#     # Create a new curve and object
#     curve_data = bpy.data.curves.new(name, type="CURVE")
#     curve_data.dimensions = '3D'

#     # Create a new spline in the curve
#     spline = curve_data.splines.new(type='POLY')
#     spline.points.add(count=len(points)-1)

#     for i, pt in enumerate(points):
#         spline.points[i].co = Vector(pt).resized(4)

#     return create_object(name, curve_data)
