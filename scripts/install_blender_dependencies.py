import shutil
import subprocess
import sys
import tomllib  # Python 3.11+ only
from pathlib import Path

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
    bl_version = blender_version(major_minor=True)
    bl_python_root = bl_path / bl_version / "python"

    # Blender's bundled CPython minor version changes between Blender releases
    # (e.g. Blender 4.5 ships python3.11, Blender 5.1 ships python3.13), so we
    # discover it from the interpreter on disk rather than hardcoding it.
    bl_python_candidates = sorted(bl_python_root.glob("bin/python3.*"))
    if not bl_python_candidates:
        raise FileNotFoundError(f"Could not find a bundled Python interpreter under {bl_python_root / 'bin'}")
    bl_python = bl_python_candidates[0]
    bl_python_minor = bl_python.name.removeprefix("python")  # e.g. "3.13"
    bl_site_packages = bl_python_root / "lib" / f"python{bl_python_minor}" / "site-packages"

    # Ensure pip is installed and up to date
    subprocess.run([bl_python, "-m", "ensurepip", "--upgrade"], check=True)
    subprocess.run([bl_python, "-m", "pip", "install", "--upgrade", "pip"], check=True)

    # Separate dependencies into regular and compiled packages
    all_deps = pyproject["project"]["dependencies"]

    # Exclude bpy, mathutils (already in Blender), and pytriwild (needs special handling)
    regular_deps = [
        d
        for d in all_deps
        if not d.startswith("bpy") and not d.startswith("mathutils") and not d.startswith("pytriwild")
    ]

    # Install regular dependencies via pip
    if regular_deps:
        print(f"Installing {len(regular_deps)} regular dependencies...")
        subprocess.run([bl_python, "-m", "pip", "install", *regular_deps], check=True)
        print(f"✓ Installed {len(regular_deps)} dependencies")

    # Copy pre-compiled pytriwild from .venv to Blender
    copy_precompiled_package("pytriwild", bl_site_packages)

    print("\n✓ All Blender dependencies successfully installed!")


def copy_precompiled_package(package_name: str, target_site_packages: Path):
    """Copy a pre-compiled package from .venv to Blender's site-packages.

    Args:
        package_name: Name of the package (e.g., 'pytriwild')
        target_site_packages: Path to Blender's site-packages directory
    """
    # Find .venv site-packages
    venv_site_packages = (
        Path(sys.prefix) / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
    )

    if not venv_site_packages.exists():
        raise FileNotFoundError(f"Could not find .venv site-packages at {venv_site_packages}")

    # Find all files related to the package
    package_files = list(venv_site_packages.glob(f"{package_name}*"))

    if not package_files:
        raise FileNotFoundError(
            f"Package '{package_name}' not found in .venv.\n"
            f"Please ensure it's installed in your .venv first:\n"
            f"  uv sync --dev"
        )

    print(f"\nCopying pre-compiled {package_name} from .venv to Blender...")

    for src_path in package_files:
        dest_path = target_site_packages / src_path.name

        if src_path.is_file():
            print(f"  Copying {src_path.name}...")
            shutil.copy2(src_path, dest_path)
        elif src_path.is_dir():
            print(f"  Copying {src_path.name}/...")
            if dest_path.exists():
                shutil.rmtree(dest_path)
            shutil.copytree(src_path, dest_path)

    print(f"✓ {package_name} copied successfully")


if __name__ == "__main__":
    main()
