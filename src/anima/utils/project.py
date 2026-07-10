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
def get_main_file_path() -> Path:
    """Get the main.py file path from the project.
    Returns:
        Path: The path to the main.py file.
    Raises:
        FileNotFoundError: If main.py does not exist in the expected location.
    """
    proj_root = get_project_root_path()
    main_path = proj_root / "src" / "anima" / "main.py"
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
    for name in modules_to_delete:
        del sys.modules[name]


# Private functions ------------------------------------------------------------------------------------------
