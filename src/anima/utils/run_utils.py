import os
import sys
import threading
import psutil
import functools
import subprocess
from pathlib import Path
from anima.utils.project_utils import get_main_file_path, get_project_root_path, get_pyproject_config_value
from anima.diagnostics.logger import logger

PROJECT_NAME = 'anima'
TESTS_DIR = 'tests'


@functools.lru_cache(maxsize=1)
def get_blender_executable_path() -> Path:
    """Get Blender executable path from project config.
    Returns:
        Path: The path to the Blender executable.
    Raises:
        FileNotFoundError: If Blender path does not exist.
    """
    # Load Blender configuration from pyproject.toml
    blender_cfg = get_pyproject_config_value('tool.blender', {})
    root_dir = Path(blender_cfg.get('root-dir', '')).expanduser()

    # Get the Blender executable path
    bl_path = root_dir / 'blender'
    if not bl_path.exists():
        raise FileNotFoundError(
            f"Blender path does not exist: {bl_path}")
    return bl_path


def check_blender_run_status() -> tuple[bool, subprocess.Popen | None]:
    """Check if Blender is already running.
    Returns:
        bool: True if Blender is running, else False.
        subprocess.Popen | None: The running Blender process or None if not found.
    """
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if 'blender' in proc.info['name'].lower():
                return True, proc
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False, None


def get_running_blender_process() -> tuple[subprocess.Popen, bool]:
    """Start Blender if not already running and return the running process.
    Returns:
        tuple[subprocess.Popen, bool]: The Blender process and a boolean indicating if an already running Blender instance was found (requiring script reload).
    """
    running, proc = check_blender_run_status()
    if running:
        logger.debug(f"Found running Blender instance (pid: {proc.pid})")
    else:
        proc = start_blender_instance()
    return proc, running


def start_blender_instance() -> subprocess.Popen:
    """Start Blender with GUI in a separate window.
    Returns:
        subprocess.Popen: The process handle for the started Blender instance.
    Raises:
        FileNotFoundError: If Blender executable is not found.
        subprocess.SubprocessError: If there is an error starting Blender."""
    try:
        # Start Blender with GUI (no --background flag)
        bl_path = get_blender_executable_path()
        main_path = get_main_file_path()
        logger.info(f"Starting Blender from: {bl_path}")
        logger.info(f"Using main.py: {main_path}")
        process = subprocess.Popen([bl_path, '--python', main_path],
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   text=True,
                                   bufsize=1)

        # Check if it's already dead (immediate failure)
        if process.poll() is not None and process.returncode != 0:
            stderr = process.stderr.read()
            raise subprocess.SubprocessError(
                f"Blender failed to start with error: {stderr}"
            )

        # Verify that Blender is running, and start output monitoring
        running, proc = check_blender_run_status()
        assert proc.pid == process.pid, "Started Blender process ID mismatch"
        if running:
            logger.info(f"Blender started (pid: {process.pid})")
            start_output_monitoring(process)
            return process
        else:
            logger.error("Blender failed to start")
            return None

    except (FileNotFoundError, subprocess.SubprocessError) as e:
        logger.error(f"Could not start Blender: {e}")
        return None


def start_output_monitoring(process):
    """Start threads to monitor Blender output"""

    def read_stream(stream):
        try:
            while True:
                line = stream.readline()
                if not line:  # Empty string means EOF
                    break
                print(f"{line.rstrip()}")
        except Exception as e:
            logger.error(f"Error reading line: {e}")

    threads = []
    streams = [process.stdout, process.stderr]
    for stream in streams:
        if stream:  # Check if stream exists
            t = threading.Thread(
                target=read_stream,
                args=(stream,),
                daemon=True
            )
            t.start()
            threads.append(t)

    return threads


def cleanup_blender_instance(bl_process: subprocess.Popen):
    """Clean up Blender process if we started it.
    Args:
        bl_process(subprocess.Popen): The Blender process to clean up.
    """
    if bl_process:
        try:
            logger.info(f"Stopping Blender process (pid: {bl_process.pid})")
            bl_process.terminate()

            # Wait for graceful shutdown
            try:
                bl_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning(
                    "Blender didn't terminate gracefully, forcing kill")
                bl_process.kill()

        except (ProcessLookupError, AttributeError):
            # Process already terminated
            pass


def reload_project_in_blender():
    """Reload main.py in the already running Blender instance using Blender's - -python-expr via command line."""
    configure_reload()

    # Find the running Blender process
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if 'blender' in proc.info['name'].lower():
                blender_pid = proc.info['pid']
                break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    else:
        logger.error("No running Blender process found to reload main.py")
        return

    # Use xdg-open to send a script to Blender via its Python API
    # This requires Blender to be started with --enable-autoexec or have scripting enabled
    # We'll use Blender's --python-expr to execute a reload command
    blender_path = get_blender_executable_path()
    main_py_path = Path('src')/'anima/main.py'
    expr = f"exec(compile(open(r'{main_py_path}').read(), r'{main_py_path}', 'exec'))"

    try:
        subprocess.run([str(blender_path), '--python-expr', expr])
        logger.info("Reloaded main.py in running Blender instance.")
    except Exception as e:
        logger.error(f"Failed to reload main.py in running Blender: {e}")


def configure_reload():
    """Configure the script to auto-reload modules when changes are made."""
    # Delete all project-related modules from sys.modules
    modules_to_delete = [
        module_name for module_name in sys.modules.keys()
        if module_name.startswith(PROJECT_NAME) or module_name.startswith(TESTS_DIR)
    ]
    for module_name in modules_to_delete:
        del sys.modules[module_name]
