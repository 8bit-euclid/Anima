from apeiron.globals.general import get_blender_object
from apeiron.globals.easybpy import create_driver


class Driver:
    def __init__(self):
        self.bl_driver = None
        self.variables = []

    def set_output_variable(self, object, bl_data_path, index=-1):
        bl_obj = get_blender_object(object)
        self.bl_driver = create_driver(bl_obj, bl_data_path, index)
        assert not isinstance(
            self.bl_driver, list), f'Please specify the component index of the vector attribute \'{bl_data_path}\''
        return self

    def add_input_variable(self, name, object, bl_data_path):
        assert self.bl_driver, 'The driven variable has not yet been set'

        # Setup variable
        var = self.bl_driver.variables.new()
        var.name = name
        var.type = 'SINGLE_PROP'  # Todo: TRANSFORMS, LOC_DIFF, ROTATION_DIFF, CONTEXT_PROP

        # Add target components
        target = var.targets[0]
        target.id_type = 'OBJECT'
        target.id = get_blender_object(object)
        target.data_path = bl_data_path

        self.variables.append(var)
        return self

    def set_expression(self, expression: str):
        assert self.bl_driver, 'The driven variable has not yet been set'

        for v in self.variables:
            assert v.name in expression, f'Variable \'{v.name}\' is not in the expression \'{expression}\''

        self.bl_driver.type = 'SCRIPTED'
        self.bl_driver.expression = expression
        return self
