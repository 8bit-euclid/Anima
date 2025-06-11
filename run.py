import sys
import os
import importlib
from pathlib import Path

PROJECT_NAME = 'anima'
TESTS_DIR = 'tests'


def run():
    """Run the main module of the project."""
    configure_python_path()
    configure_reload()

    # Load and run the main module
    proj = importlib.import_module(f'{PROJECT_NAME}.main')
    proj.main()


def configure_python_path():
    """Add the project root and the src directory to the Python path."""
    root_dir = Path(__file__).parent
    src_dir = root_dir/'src'
    sys.path.insert(0, str(root_dir))
    sys.path.insert(0, str(src_dir))


def configure_reload():
    """Configure the script to auto-reload modules when changes are made."""
    # Delete all project-related modules from sys.modules
    modules_to_delete = [
        module_name for module_name in sys.modules.keys()
        if module_name.startswith(PROJECT_NAME) or module_name.startswith(TESTS_DIR)
    ]
    for module_name in modules_to_delete:
        del sys.modules[module_name]


run()
