import math

class Vector:
   def __init__(self, x: float, y: float, z: float = 0) -> None:
      self.__x_fn = x if callable(x) else lambda t: x
      self.__y_fn = y if callable(y) else lambda t: y
      self.__z_fn = z if callable(z) else lambda t: z
      self.__dynamic = callable(x) or callable(y) or callable(z)

   def x(self, t: float = None):
      self.__check_parameter(t)
      return self.__x_fn(t)
   
   def y(self, t: float = None):
      self.__check_parameter(t)
      return self.__y_fn(t)
   
   def z(self, t: float = None):
      self.__check_parameter(t)
      return self.__z_fn(t)
   
   def coordinates(self, t: float = None):
      return self.x(t), self.y(t), self.z(t)
   
   def norm(self, t: float = None):
      return math.sqrt(self.x(t) ** 2 + self.y(t) ** 2 + self.z(t) ** 2)
   
   def dot(self, other, t: float = None):
      assert isinstance(other, Vector), "Expected an instance of the Vector class."
      return self.x(t) * other.x(t) + \
             self.y(t) * other.y(t) + \
             self.z(t) * other.z(t)
   
   def cross(self, other, t: float = None):
      assert isinstance(other, Vector), "Expected an instance of the Vector class."
      return Vector(self.y(t) * other.z(t) - self.z(t) * other.y(t), 
                    self.z(t) * other.x(t) - self.x(t) * other.z(t), 
                    self.x(t) * other.y(t) - self.y(t) * other.x(t))
   
   def __check_parameter(self, t):
      if self.__dynamic:
         assert t is not None, "Expected a parameter specification for a dynamic Vector type."
   
Point = Vector

def x_fn(t):
    return t

def y_fn(t):
    return t ** 2

def z_fn(t):
    return 2 * t

# p = Point(1.0, y_fn)
p = Point(1.0, 2.0)
print(f"{p.x()}, {p.y()}, {p.z()}")
print(f"{p.x(1)}, {p.y(1)}, {p.z(1)}")
print(f"{p.x(2)}, {p.y(2)}, {p.z(2)}")
print(f"{p.x(2.0)}, {p.y(2.0)}, {p.z(2.0)}")