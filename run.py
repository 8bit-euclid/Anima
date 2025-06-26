# fmt: off
# Ensure the src directory is in the Python path
import sys
from pathlib import Path
src_dir = Path(__file__).parent / 'src'
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# Now, import modules as usual
from anima.diagnostics import logger
from anima.utils.run_utils import (get_running_blender_process,
                                   configure_reload,
                                   reload_project_in_blender,
                                   cleanup_blender_instance)
# fmt: on


def run():
    """Run the main module of the project."""
    configure_reload()

    bl_proc = None  # Blender process handle
    try:
        # Ensure Blender is running with GUI before executing the main script
        bl_proc = get_running_blender_process()

        if not bl_proc:
            # Blender is already running, so reload main.py in the running instance
            reload_project_in_blender()

    except KeyboardInterrupt:
        logger.info("Script interrupted by user")

    except Exception as e:
        logger.error(f"Error running script: {e}")
        raise

    # finally:
    #     # Clean up Blender if we started it
    #     cleanup_blender_instance(bl_proc)


if __name__ == '__main__':
    run()
