# from functools import partial


# class A:
#     def __init__(self, **values):
#         set_attr = partial(object.__setattr__, self)

#         set_attr('id', 0)
#         for name, value in values.items():
#             set_attr(name, value)
#         set_attr('_storage', {})
#         set_attr('_initilised', False)

#     def __getattribute__(self, name):
#         """
#         Called for all attribute access. This lets us control the lookup order
#         and properly handle both instance and class attributes.
#         """
#         get_attr = partial(object.__getattribute__, self)

#         # First get the superclass's __getattribute__ to access special attributes
#         try:
#             return get_attr(name)
#         except AttributeError:
#             # If it's not a special attribute, check if we're initialized
#             if get_attr('_initilised'):
#                 # Check storage dictionary for regular attributes
#                 storage = get_attr('_storage')
#                 if name in storage:
#                     return storage[name]

#                 # If not in storage, check class attributes
#                 cls = get_attr('__class__')
#                 if hasattr(cls, name):
#                     return get_attr(name)

#                 raise AttributeError(
#                     f"'{cls.__name__}' object has no attribute '{name}'")
#             else:
#                 # During initialization, use normal attribute lookup
#                 return get_attr(name)

#     def __getattr__(self, name):
#         print('__getattr__')
#         # If __getattribute__ fails to find an attribute, this is called
#         # Provide a custom error or return a default value if needed
#         raise AttributeError(
#             f"'{type(self).__name__}' object has no attribute '{name}'")

#     def __setattr__(self, name, value):
#         # print('__setattr__')
#         # # Redirect dynamic attributes to the dictionary
#         # if hasattr(self, '_storage') and name not in dir(type(self)):
#         #     self._storage[name] = value
#         # else:
#         #     # Otherwise, set the attribute normally
#         #     super().__setattr__(name, value)
#         """
#         Called when setting any attribute
#         """
#         set_attr = partial(object.__setattr__, self)

#         # Handle special attributes and class attributes normally
#         if name.startswith('_'):
#             set_attr(name, value)
#             if name == '_initilised':
#                 # When initialization is complete, move all existing attributes to storage
#                 if value:
#                     for attr_name, attr_value in vars(self).items():
#                         if not attr_name.startswith('_'):
#                             self._storage[attr_name] = attr_value
#                             object.__delattr__(self, attr_name)
#             return

#         # If we're not initialized, set attributes normally
#         if not self._initilised:
#             set_attr(name, value)
#             return

#         # Store everything else in our dictionary
#         self._storage[name] = value

#     def __str__(self):
#         # attrs = super().__getattribute__('__dict__')
#         # return f'Attrs: {attrs}'
#         d = {k: v for k, v in self.__dict__.items() if k != '_storage'}
#         return f'Attrs: {d}' + f'\nCustoms: {self._storage}'

#     def set_x(self, x):
#         self.x = x


# class B(A):
#     def __init__(self, **values):
#         set_attr = partial(object.__setattr__, self)
#         # set_attr('u', -1)
#         self.u = -1
#         B.update(self)
#         super().__init__(**values)

#     def update(self):
#         print('Updating...')


# def main():
#     a = B(x=1, y=2)
#     a.z = 10.0
#     print(a)
#     # a.set_x(3)
#     # print('x:', a.x)
#     # print('y:', a.y)
#     # print('z:', a.z)


# class Object(ABC):
#     """
#     Base class from which all visualisable objects will derive. Contains common members and methods, and
#     encapsulates the underlying Blender object.
#     """

#     def __init__(self, bl_object=None, name='Object', **kwargs):
#         set_attr = super().__setattr__
#         get_attr = super().__getattribute__

#         if bl_object is not None:
#             bl_object.name = name
#         set_attr('name', name)
#         set_attr('bl_obj', bl_object)
#         set_attr('parent', None)
#         set_attr('children', [])
#         set_attr('shape_keys', [])
#         set_attr('hooks', [])
#         set_attr('_write_logs', False)

#     def __getattribute__(self, name):
#         get_attr = super().__getattribute__

#         # Check if the name exists in the custom properties
#         # init_attrs = get_attr('_init_attrs')
#         bl_obj = get_attr('bl_obj')
#         if name in bl_obj.keys():
#             return bl_obj[name]
#         # Otherwise, delegate to the default behavior
#         return get_attr(name)

#     def __getattr__(self, name):
#         # If __getattribute__ fails to find an attribute, this is called
#         # Provide a custom error or return a default value if needed
#         raise AttributeError(
#             f"'{type(self).__name__}' object has no attribute '{name}'")

#     def __setattr__(self, name, value):
#         get_attr = super().__getattribute__
#         set_attr = super().__setattr__

#         # Redirect dynamic attributes to the dictionary
#         if hasattr(self, 'bl_obj') and name not in dir(type(self)):
#             # if hasattr(self, 'bl_obj') and name not in get_attr('_init_attrs'):
#             get_attr('bl_obj')[name] = value
#         else:
#             # Otherwise, set the attribute normally
#             set_attr(name, value)
