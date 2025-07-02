from pathlib import Path
from anima.diagnostics import logger
from anima.utils.project import configure_project_reload, get_main_file_path

RELOAD_SCRIPT_PATH = Path(__file__).parent / "scripts" / "reload.py"


class BlenderScriptReloader:
    """Handles script reloading in Blender."""

    def __init__(self, process_manager):
        self._process_manager = process_manager

    def reload(self) -> bool:
        """Reload the main script."""
        if not self._process_manager.is_running():
            logger.error("Blender process is no longer running")
            return False

        try:
            configure_project_reload()

            with open(RELOAD_SCRIPT_PATH, 'r') as f:
                template = f.read()

            reload_script = template.format(main_path=get_main_file_path())
            self._process_manager.process.stdin.write(reload_script + '\n')
            self._process_manager.process.stdin.flush()

            return True

        except Exception as e:
            logger.error(f"Error sending reload command: {e}")
            return False
