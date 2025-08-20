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
def get_project_root_path(on_host: bool = True, marker: str = ".git") -> Path:
    """Find the root directory of the project by looking for a 'marker' file.
    Args:
        on_host (bool): Whether the path is on the host machine or the container.
        marker (str): The name of the file that indicates the project root (default is '.git').
    Returns:
        Path: The path to the project root directory.
    Raises:
        FileNotFoundError: If the marker file is not found in any parent directories."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / marker).exists():
            # Handle path resolution based on environment:
            # If running in container and host path requested, map the path
            path = parent
            if running_in_container() and on_host:
                path = _map_container_to_host_path(parent)

            logger.trace(f"Project root found: {path}")
            return path

    raise FileNotFoundError(f"Project root not found. Ensure it contains {marker}.")


@functools.lru_cache(maxsize=1)
def get_main_file_path(on_host: bool = True) -> Path:
    """Get the main.py file path from the project.
    Args:
        on_host (bool): Whether the path is on the host machine or the container.
    Returns:
        Path: The path to the main.py file.
    Raises:
        FileNotFoundError: If main.py does not exist in the expected location.
    """
    proj_root = get_project_root_path(on_host=on_host)
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


@functools.lru_cache()
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


def configure_project_reload():
    """Configure the script to auto-reload modules when changes are made."""

    # Delete all project-related modules from sys.modules
    modules_to_delete = [
        name
        for name in sys.modules.keys()
        if name.startswith(get_project_name()) or name.startswith("tests")
    ]
    for name in modules_to_delete:
        del sys.modules[name]


def running_in_container() -> bool:
    """Check if running inside a Docker container.
    Returns:
        bool: True if running in a container, False otherwise."""

    # Check for Docker environment file
    if Path("/.dockerenv").exists():
        return True

    # Check for container indicator in cgroup
    try:
        cgroup_content = Path("/proc/1/cgroup").read_text(errors="ignore")
        return "container" in cgroup_content
    except (OSError, IOError):
        return False


# Private functions ------------------------------------------------------------------------------------------


def _map_container_to_host_path(container_path: Path) -> Path:
    """Map container path to host path based on volume mounts."""
    path_str = str(container_path)

    # Map workspace paths
    if path_str.startswith("/workspace"):
        return Path(path_str.replace("/workspace", "${localWorkspaceFolder}"))

    # Map Blender paths
    if path_str.startswith("/home/vscode/Applications/blender"):
        return Path(
            path_str.replace(
                "/home/vscode/Applications/blender",
                "${localEnv:HOME}/Applications/blender",
            )
        )

    # Return unchanged if no mapping needed
    return container_path


def _map_host_to_container_path(host_path: Path) -> Path:
    """Map host path to container path (theoretical reverse mapping)."""
    path_str = str(host_path)

    # This is a theoretical case - typically not needed
    # but included for completeness
    if "${localWorkspaceFolder}" in path_str:
        return Path(path_str.replace("${localWorkspaceFolder}", "/workspace"))

    if "${localEnv:HOME}/Applications/blender" in path_str:
        return Path(
            path_str.replace(
                "${localEnv:HOME}/Applications/blender",
                "/home/vscode/Applications/blender",
            )
        )

    # Return unchanged if no mapping needed
    return host_path
