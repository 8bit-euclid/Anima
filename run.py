import sys
import os
import importlib

PROJECT_NAME = 'anima'


def configure_reload():
    """Configure the script to auto-reload modules when changes are made."""
    # Add the project root directory to sys.path
    root_dir = os.path.dirname(os.path.abspath(__file__))
    if root_dir not in sys.path:
        sys.path.append(root_dir)

    # Delete all anima-related modules from sys.modules (only matters when reloading)
    for module in list(sys.modules.keys()):
        if PROJECT_NAME in module:
            del sys.modules[module]


def run():
    """Run the main module of the project."""
    configure_reload()

    # Load and run the main module
    proj = importlib.import_module(PROJECT_NAME + '.main')
    proj.main()


run()
