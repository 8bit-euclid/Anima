from .base import *


class Polygon(BaseObject):
    def __init__(self, vertices):
        self.vertices = vertices


class Triangle(Polygon):
    def __init__(self, vertices):
        assert len(vertices) == 3, 'Expected 3 vertices for a triangle'
        super().__init__(vertices)


class Rectangle(Polygon):
    def __init__(self, origin, ):
        assert len(vertices) == 4, 'Expected 4 vertices for a triangle'
        self.vertices = vertices
