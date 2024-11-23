import sys
import os
import importlib

proj_name = 'apeiron'

# Add the project root directory to sys.path
root_dir = os.path.dirname(os.path.abspath(__file__))
if root_dir not in sys.path:
    sys.path.append(root_dir)

# Delete all apeiron-related modules (only applies when reloading)
for module in list(sys.modules.keys()):
    if proj_name in module:
        del sys.modules[module]

# Load main module
proj = importlib.import_module(proj_name + '.main')

# Run main routine
proj.main()
