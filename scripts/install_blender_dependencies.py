import subprocess
import tomllib  # Python 3.11+ only
from anima.globals.general import get_pyproject_path
from anima.utils.blender import get_blender_root_path


# Note: This script assumes that the blender Python path has been set in the pyproject.toml file


def main():
    # Parse dependencies from pyproject.toml and get blender Python path
    with open(get_pyproject_path(), "rb") as f:
        pyproject = tomllib.load(f)

    bl_path = get_blender_root_path()
    bl_python = bl_path/'4.3'/'python'/'bin'/'python3.11'

    # Ensure pip is installed and up to date
    subprocess.run(
        [bl_python, "-m", "ensurepip", "--upgrade"], check=True)
    subprocess.run([bl_python, "-m", "pip", "install",
                   "--upgrade", "pip"], check=True)

    # Install dependencies
    deps = pyproject["project"]["dependencies"]
    subprocess.run([bl_python, "-m", "pip", "install", *deps], check=True)


if __name__ == "__main__":
    main()
