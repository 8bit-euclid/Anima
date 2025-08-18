import functools
import sys
import tomllib
from pathlib import Path

from anima.diagnostics import logger


@functools.lru_cache(maxsize=1)
def get_project_name() -> str:
    """Get the project name from the pyproject.toml file.
    Returns:
        str: The project name."""
    return get_pyproject_config_value("project.name", default="Unknown")


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
def get_main_file_path() -> Path:
    """Get the main.py file path from the project.
    Returns:
        Path: The path to the main.py file.
    Raises:
        FileNotFoundError: If main.py does not exist in the expected location.
    """
    project_root = get_project_root_path()
    main_path = project_root / "src" / "anima" / "main.py"
    if not main_path.exists():
        raise FileNotFoundError(f"Main file not found: {main_path}")
    logger.trace(f"Main file path: {main_path}")
    return main_path


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


@functools.lru_cache()
def get_pyproject_config_value(key_path: str, default=None):
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


def configure_project_reload():
    """Configure the script to auto-reload modules when changes are made."""
    # Delete all project-related modules from sys.modules
    modules_to_delete = [
        module_name
        for module_name in sys.modules.keys()
        if module_name.startswith(get_project_name()) or module_name.startswith("tests")
    ]
    for module_name in modules_to_delete:
        del sys.modules[module_name]
