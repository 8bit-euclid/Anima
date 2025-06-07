# class Variable:
#     def __init__(self, name: str, driver):
#         self.var = driver.variables.new()
#         self.var.name = name
#         self.num_components = 0

#     def add_component(self, object, data_path):
#         # Check if the variable has at least one component and resize targets
#         if self.num_components > 0:
#             # self.var.targets.append(None)
#             raise Exception(
#                 "Only a single component can be added to a variable")
#         self.num_components += 1

#         # Add new target
#         self.var.targets[-1].id_type = 'OBJECT'
#         self.var.targets[-1].id = object
#         self.var.targets[-1].data_path = data_path
