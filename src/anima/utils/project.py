import functools
import importlib
import os
import sys
import tomllib
from pathlib import Path

from anima.diagnostics import logger


@functools.lru_cache(maxsize=1)
def get_project_name() -> str:
    """Get the project name from the pyproject.toml file.
    Returns:
        str: The project name."""
    return get_pyproject_config_entry("project.name", default="Unknown")


@functools.lru_cache(maxsize=1)
def get_project_root_path(marker: str = ".git") -> Path:
    """Find the root directory of the project by looking for a 'marker' file.
    Args:
        marker (str): The name of the file that indicates the project root (default is '.git').
    Returns:
        Path: The path to the project root directory.
    Raises:
        FileNotFoundError: If the marker file is not found in any parent directories."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / marker).exists():
            logger.trace(f"Project root found: {parent}")
            return parent

    raise FileNotFoundError(f"Project root not found. Ensure it contains {marker}.")


@functools.lru_cache(maxsize=1)
def get_script_path() -> Path:
    """Get the path to the script Blender needs to run.

    Resolution order:
      1. `ANIMA_SCRIPT` env var (path to a lesson script), if set and non-empty.
      2. Fallback to the framework's default demo scene: src/anima/main.py.

    Returns:
        Path: The resolved script path.
    Raises:
        FileNotFoundError: If the resolved path does not exist.
    """
    override = os.environ.get("ANIMA_SCRIPT", "").strip()
    if override:
        script_path = Path(override).expanduser().resolve()
        if not script_path.exists():
            raise FileNotFoundError(f"ANIMA_SCRIPT points to a non-existent file: {script_path}")
        logger.trace(f"Using script from ANIMA_SCRIPT: {script_path}")
        return script_path

    proj_root = get_project_root_path()
    main_path = proj_root / "src" / "anima" / "main.py"
    if not main_path.exists():
        raise FileNotFoundError(f"Main file not found: {main_path}")
    logger.trace(f"Main file path: {main_path}")
    return main_path


def get_course_root() -> Path:
    """Get the course root directory for the currently running lesson script.

    Assumes the standard layout: <course_root>/lessons/<lesson_script>.py

    Returns:
        Path: The course root directory.
    """
    return get_script_path().parent.parent


def import_course_module(module_name: str):
    """Import a module from the current lesson's course package.

    Adds the course's parent directory to `sys.path` (once) so the course folder
    itself is importable as a package, then imports `<course_pkg>.<module_name>`.

    Args:
        module_name (str): Dotted path relative to the course root, e.g. "common.styles".
    Returns:
        module: The imported module.
    """
    course_root = get_course_root()
    courses_root = course_root.parent
    if str(courses_root) not in sys.path:
        sys.path.insert(0, str(courses_root))

    return importlib.import_module(f"{course_root.name}.{module_name}")


def import_shared_module(module_name: str):
    """Import a module from the shared `common/` package at the Courses root.

    Adds the Courses root to `sys.path` (once) so the `common/` package is importable, then imports
    `common.<module_name>`.

    Args:
        module_name (str): Dotted path relative to the `common/` package, e.g. "utils.helpers".
    Returns:
        module: The imported module.
    """
    courses_root = get_course_root().parent
    if str(courses_root) not in sys.path:
        sys.path.insert(0, str(courses_root))
    return importlib.import_module(f"common.{module_name}")


@functools.lru_cache(maxsize=1)
def get_pyproject_config() -> dict:
    """Load, cache, and retrieve the entire pyproject.toml config.
    Returns:
        dict: The parsed configuration from pyproject.toml.
    Raises:
        FileNotFoundError: If pyproject.toml does not exist.
        tomllib.TOMLDecodeError: If the file is not a valid TOML."""
    try:
        with open("pyproject.toml", "rb") as f:
            return tomllib.load(f)
    except Exception as e:
        logger.error(f"Failed to load pyproject.toml: {e}")
        return {}


@functools.lru_cache
def get_pyproject_config_entry(key_path: str, default=None):
    """Retrieve a value from pyproject.toml using a dotted key path.
    Args:
        key_path (str): Dotted key path (e.g. 'tool.blender').
        default: Default value to return if the key is not found.
    Returns:
        The value found at the specified key path, or the default value if not found."""
    keys = key_path.split(".")
    config = get_pyproject_config()
    value = config
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default
    return value


def get_blender_config():
    """Get Blender configuration from pyproject.toml.
    Returns:
        dict: The Blender configuration from pyproject.toml."""
    return get_pyproject_config_entry("tool.blender")


def validate_project_configuration():
    """Validate that required project configuration is set in pyproject.toml."""
    errors = []
    path = get_blender_config().get("install-dir", "")
    if not path:
        errors.append("Blender path is not set in pyproject.toml")
    elif not Path(path).expanduser().exists():
        errors.append(f"Blender path does not exist: {Path(path).expanduser()}")

    if errors:
        error_list = "\n".join(f"  - {error}" for error in errors)
        logger.error(
            f"Project configuration validation failed:\n{error_list}\n\n\
            Please update your pyproject.toml file with the required configuration."
        )


def configure_project_reload():
    """Configure the script to auto-reload modules when code changes are detected."""

    proj_name = get_project_name()
    # CRITICAL: The socket server singleton must survive reloads. Evicting its module would
    # make main.py create a fresh server that fights the live one over the TCP port.
    preserved = (f"{proj_name}.utils.socket",)

    # Delete all project-related modules (except the preserved ones) from sys.modules to force reloads.
    modules_to_delete = [
        name
        for name in sys.modules.keys()
        if (name.startswith(proj_name) or name.startswith("tests")) and not name.startswith(preserved)
    ]

    # Also evict the current lesson's course package (common utilities, etc.) so hot
    # reload picks up edits to course-shared code, not just the lesson script itself.
    try:
        course_pkg = get_course_root().name
        modules_to_delete += [name for name in sys.modules if name == course_pkg or name.startswith(f"{course_pkg}.")]
    except FileNotFoundError:
        pass

    for name in modules_to_delete:
        del sys.modules[name]


# Private functions ------------------------------------------------------------------------------------------
