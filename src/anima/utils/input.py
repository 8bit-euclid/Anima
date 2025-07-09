import bpy
import keyboard
from anima.diagnostics import logger
from anima.utils.socket.client import BlenderSocketClient


class BlenderInputMonitor:
    def __init__(self, socket_client: BlenderSocketClient):
        self._socket = socket_client
        # self.setup_hotkeys()

    # def setup_hotkeys(self):
    #     # Set up global hotkeys
    #     keyboard.add_hotkey('ctrl+r', self.reload_script)
    #     keyboard.add_hotkey('ctrl+shift+q', self.stop_blender)
    #     keyboard.add_hotkey('ctrl+shift+s', self.get_status)
    #     logger.info("Hotkeys registered:")
    #     logger.info("  Ctrl+R: Reload script")
    #     logger.info("  Ctrl+Shift+Q: Stop Blender")
    #     logger.info("  Ctrl+Shift+S: Get status")

    def _reload(self):
        try:
            logger.info("Reloading script...")
            # Fallback: re-execute the file
            with open(self._script_path, 'r') as f:
                code = f.read()
            exec(code, globals())
            logger.info("Script re-executed successfully")

        except Exception as e:
            logger.error(f"Script reload failed: {e}")
