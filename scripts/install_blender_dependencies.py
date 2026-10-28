import subprocess
import tomllib  # Python 3.11+ only

from anima.globals.general import get_pyproject_path
from anima.utils.blender import get_blender_python_path
from anima.utils.project import validate_project_configuration

# Note: This script assumes that the blender Python path has been set in the pyproject.toml file


def main():
    validate_project_configuration()

    # Parse dependencies from pyproject.toml and get blender Python path
    with open(get_pyproject_path(), "rb") as f:
        pyproject = tomllib.load(f)

    bl_python = get_blender_python_path()

    # Ensure pip is installed and up to date
    subprocess.run([bl_python, "-m", "ensurepip", "--upgrade"], check=True)
    subprocess.run([bl_python, "-m", "pip", "install", "--upgrade", "pip"], check=True)

    # bpy and mathutils already ship with Blender
    deps = [d for d in pyproject["project"]["dependencies"] if not d.startswith(("bpy", "mathutils"))]

    if deps:
        print(f"Installing {len(deps)} dependencies...")
        subprocess.run([bl_python, "-m", "pip", "install", *deps], check=True)
        print(f"✓ Installed {len(deps)} dependencies")

    print("\n✓ All Blender dependencies successfully installed!")


if __name__ == "__main__":
    main()
