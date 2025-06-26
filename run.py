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
    bl_proc = None
    try:
        bl_proc, reload = get_running_blender_process()
        if reload:
            reload_project_in_blender()
    except Exception as e:
        logger.error(f"Error running script: {e}")
        if bl_proc:
            cleanup_blender_instance(bl_proc)
        raise

    try:
        logger.info("Monitoring Blender output... Press Ctrl+C to stop")
        bl_proc.wait()  # blocks until Blender exits
        logger.info(f"Blender process {bl_proc.pid} has ended")

    except KeyboardInterrupt:
        pass

    finally:
        cleanup_blender_instance(bl_proc)


if __name__ == '__main__':
    run()
