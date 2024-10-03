import ast
import inspect
import shutil
import os
import textwrap
from . import temp


# Add all modules with custom driver function definitions here.
scan_modules = [temp]


def is_driver_callable(obj):
    """ Checks if a function/method has been marked to be added to the driver namespace. """

    return inspect.isfunction(obj) and hasattr(obj, 'driver_callable') and obj.driver_callable


def remove_decorators(src_code):
    """ Removes decorators from the source code of a function/method. """

    # Parse the source code into an AST (Abstract Syntax Tree)
    tree = ast.parse(src_code)

    # Find the function definition (FunctionDef)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            # Remove the decorators
            node.decorator_list = []
            # Unparse (convert back to source code)
            return ast.unparse(node)
    return src_code


def copy_driver_callables():
    """ Copy all functions/methods flagged to be added to the driver namespace to customs.py. """

    # Get the directory of the current submodule
    curr_dir = os.path.dirname(__file__)
    file_path = os.path.join(curr_dir, 'customs.py')

    # Write all flagged functions/methods to the output file.
    with open(file_path, 'w') as out_file:
        for module in scan_modules:
            mod_name = module.__name__
            for obj_name, obj in inspect.getmembers(module):
                # Check if the object is a function and flagged.
                if is_driver_callable(obj):
                    src_code = remove_decorators(inspect.getsource(obj))
                    out_file.write(
                        f"\n\n# Function: {obj_name} in module {mod_name}\n")
                    out_file.write(src_code)

                # Check if the object is a class and has flagged methods.
                if inspect.isclass(obj):
                    for mem_name, mem in inspect.getmembers(obj):
                        if is_driver_callable(mem):
                            src_code = remove_decorators(
                                textwrap.dedent(inspect.getsource(mem)))
                            out_file.write(
                                f"\n\n# Method: {mem_name} in class {obj_name} in module {mod_name}\n")
                            out_file.write(src_code)


def copy_file(file_name, dest_dir):
    dest_dir = os.path.expanduser(dest_dir)
    curr_dir = os.path.dirname(__file__)

    # Create the full path of the source file
    src_file = os.path.join(curr_dir, file_name)

    # Ensure the destination directory exists
    if not os.path.exists(dest_dir):
        raise Exception(f'Directory {dest_dir} does not exist.')

    # Create the full path of the destination file
    dest_file = os.path.join(dest_dir, file_name)

    # Copy the file
    try:
        shutil.copy(src_file, dest_file)
    except Exception as e:
        print(f"Error while copying file: {e}")


def copy_startup_files():
    copy_driver_callables()

    # Copy Blender startup files
    dest_dir = "~/.config/blender/4.1/scripts/startup"
    for file_name in ['blender_startup.py', 'customs.py']:
        copy_file(file_name, dest_dir)
