import sys
import importlib
# import tomllib
# import subprocess
# import psutil
# import os
# import time
# import functools
from pathlib import Path
# from anima.diagnostics import logger

PROJECT_NAME = 'anima'
TESTS_DIR = 'tests'


def run():
    """Run the main module of the project."""
    # bl_process = None

    # try:
    #     # Ensure Blender is running with GUI before executing the main script
    #     bl_process = ensure_blender_running()

    #     # Give Blender extra time to fully load UI context
    #     if bl_process:
    #         logger.info("Waiting for Blender UI to fully initialize...")
    #         time.sleep(1)

    # except KeyboardInterrupt:
    #     logger.info("Script interrupted by user")

    # except Exception as e:
    #     logger.error(f"Error running script: {e}")
    #     raise

    # finally:
    #     # Clean up Blender if we started it
    #     cleanup_blender(bl_process)

    configure_python_path()
    configure_reload()

    # Load and run the main module
    proj = importlib.import_module(f'{PROJECT_NAME}.main')
    proj.main()


def configure_python_path():
    """Add the project root and the src directory to the Python path."""
    root_dir = Path(__file__).parent
    src_dir = root_dir/'src'
    sys.path.insert(0, str(root_dir))
    sys.path.insert(0, str(src_dir))


def configure_reload():
    """Configure the script to auto-reload modules when changes are made."""
    # Delete all project-related modules from sys.modules
    modules_to_delete = [
        module_name for module_name in sys.modules.keys()
        if module_name.startswith(PROJECT_NAME) or module_name.startswith(TESTS_DIR)
    ]
    for module_name in modules_to_delete:
        del sys.modules[module_name]


# def is_blender_running():
#     """Check if Blender is already running."""
#     for proc in psutil.process_iter(['pid', 'name']):
#         try:
#             if 'blender' in proc.info['name'].lower():
#                 return True
#         except (psutil.NoSuchProcess, psutil.AccessDenied):
#             continue
#     return False


# @functools.lru_cache(maxsize=1)
# def get_blender_path():
#     """Get Blender executable path from project config."""
#     try:
#         with open('pyproject.toml', 'rb') as f:
#             config = tomllib.load(f)
#         bl_config = config.get('tool', {}).get('blender', {})
#         root_dir = Path(bl_config.get('root-dir', ''))
#         blender_path = root_dir / 'blender'
#         if blender_path.exists():
#             return str(blender_path)
#     except Exception as e:
#         logger.warning(f"Error reading Blender path from pyproject.toml: {e}")

#     raise FileNotFoundError(
#         "Blender executable not found. Please set the correct path in pyproject.toml."
#     )


# def start_blender_window(blender_path):
#     """Start Blender with GUI in a separate window."""
#     try:
#         logger.info(f"Starting Blender GUI from: {blender_path}")

#         # Start Blender with GUI (no --background flag)
#         process = subprocess.Popen([blender_path])

#         # Give Blender time to start and load UI
#         time.sleep(5)

#         # Verify it started
#         if is_blender_running():
#             logger.info(
#                 f"Blender GUI started successfully with PID: {process.pid}")
#             return process
#         else:
#             logger.error("Blender failed to start")
#             return None

#     except (FileNotFoundError, subprocess.SubprocessError) as e:
#         logger.error(f"Could not start Blender: {e}")
#         return None


# def ensure_blender_running():
#     """Start Blender if not already running."""
#     if is_blender_running():
#         logger.info("Blender is already running")
#         return None

#     logger.info("Blender is not running - starting GUI...")
#     blender_path = get_blender_path()
#     return start_blender_window(blender_path)


# def cleanup_blender(blender_process):
#     """Clean up Blender process if we started it."""
#     if blender_process:
#         try:
#             logger.info(
#                 f"Stopping Blender process (PID: {blender_process.pid})")
#             blender_process.terminate()

#             # Wait for graceful shutdown
#             try:
#                 blender_process.wait(timeout=5)
#             except subprocess.TimeoutExpired:
#                 logger.warning(
#                     "Blender didn't terminate gracefully, forcing kill")
#                 blender_process.kill()

#         except (ProcessLookupError, AttributeError):
#             # Process already terminated
#             pass


run()
