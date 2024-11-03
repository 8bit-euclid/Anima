from apeiron.globals.general import get_blender_object
from apeiron.globals.easybpy import create_driver


class Driver:
    """
    Encapsulates all necessary information relating to a variable being 'driven' by one or more other 
    'driving' variables. Only one output variable per driver, currently. Any number of unique input variables 
    can be added. The expression must contain all variables (enforced). 
    """

    def __init__(self, name='Driver'):
        self.name = name
        self.bl_driver = None  # Gets set when the output variable is set
        self.inputs = []

    def set_output_variable(self, object, bl_data_path, index=-1):
        """Sets the output (driven) variable."""
        bl_obj = get_blender_object(object)
        self.bl_driver = create_driver(bl_obj, bl_data_path, index)
        assert not isinstance(
            self.bl_driver, list), f'Please specify the component index of the vector attribute \'{bl_data_path}\''
        return self

    def add_input_variable(self, name, object, bl_data_path):
        """Adds an input (driving) variable."""
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

        self.inputs.append(var)
        return self

    def set_expression(self, expression: str):
        """Sets the expression (RHS only) for computing the driven variable from the input variables."""
        assert self.bl_driver, 'The driven variable has not yet been set'

        for v in self.inputs:
            assert v.name in expression, f'Variable \'{v.name}\' is not in the expression \'{expression}\''

        self.bl_driver.type = 'SCRIPTED'
        self.bl_driver.expression = expression
        return self
