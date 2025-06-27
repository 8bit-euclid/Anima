# NOTE: This script is intended to be run in Blender's Python environment. It reloads the main.py script dynamically, allowing for hot-reloading in Blender. Do not import or run this script directly in a non-Blender environment.

import sys
import importlib

# Clear modules that might cache the main script
modules_to_remove = [
    module_name for module_name in list(sys.modules.keys())
    if module_name.startswith('__main__') or 'main' in module_name.lower()
]
for module_name in modules_to_remove:
    if module_name in sys.modules:
        del sys.modules[module_name]

# Clear any cached bytecode
importlib.invalidate_caches()

# Execute the main script afresh
try:
    # Set 'main_path' in blender_utils.py -> BlenderProcess -> _reload_project_in_blender()
    main_py = r"{main_path}"
    with open(main_py, 'r') as f:
        script_content = f.read()

    globals = {
        '__name__': '__main__',
        '__file__': main_py,
    }
    exec(script_content, globals)
    print("✓ Script reloaded successfully")

except Exception as e:
    print(f"✗ Error reloading script: {{e}}")
    import traceback
    traceback.print_exc()
