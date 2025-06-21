import subprocess
import tomllib  # Python 3.11+ only
from pathlib import Path
from anima.globals.general import get_pyproject_path


# Note: This script assumes that the blender Python path has been set in the pyproject.toml file


def main():
    # Parse dependencies from pyproject.toml and get blender Python path
    with open(get_pyproject_path(), "rb") as f:
        data = tomllib.load(f)
    deps = data["project"]["dependencies"]
    bl_python = data["tool"]["blender"]["python_path"]

    # Ensure pip is installed and up to date
    subprocess.run(
        [bl_python, "-m", "ensurepip", "--upgrade"], check=True)
    subprocess.run([bl_python, "-m", "pip", "install",
                   "--upgrade", "pip"], check=True)

    # Install dependencies
    subprocess.run([bl_python, "-m", "pip", "install", *deps], check=True)


if __name__ == "__main__":
    main()
