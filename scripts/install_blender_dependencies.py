import subprocess
import tomllib  # Python 3.11+ only

from anima.globals.general import get_pyproject_path
from anima.utils.blender import blender_version, get_blender_root_path
from anima.utils.project import validate_project_configuration

# Note: This script assumes that the blender Python path has been set in the pyproject.toml file


def main():
    validate_project_configuration()

    # Parse dependencies from pyproject.toml and get blender Python path
    with open(get_pyproject_path(), "rb") as f:
        pyproject = tomllib.load(f)

    bl_path = get_blender_root_path()

    # Get the major.minor version (e.g., "4.5" from "4.5.1")
    bl_version = blender_version(major_minor=True)
    bl_python = bl_path / bl_version / "python" / "bin" / "python3.11"

    # Ensure pip is installed and up to date
    subprocess.run([bl_python, "-m", "ensurepip", "--upgrade"], check=True)
    subprocess.run([bl_python, "-m", "pip", "install", "--upgrade", "pip"], check=True)

    # Install dependencies (excluding bpy and mathutils since they're already in Blender)
    filtered_deps = [
        d for d in pyproject["project"]["dependencies"] if not d.startswith("bpy") and not d.startswith("mathutils")
    ]

    if filtered_deps:
        subprocess.run([bl_python, "-m", "pip", "install", *filtered_deps], check=True)
        print(f"Installed {len(filtered_deps)} dependencies into Blender's Python environment")
    else:
        print("No dependencies to install (bpy excluded as it's already in Blender)")


if __name__ == "__main__":
    main()
