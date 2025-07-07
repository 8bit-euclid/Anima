import bpy
import keyboard
from typing import Callable
from anima.diagnostics import logger
from anima.utils.socket.client import BlenderSocketClient


class BlenderInputMonitor:
    def __init__(self):
        self._socket = BlenderSocketClient()
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

    def execute_code(self, code: str):
        """Execute Python code in the Blender Python environment.
        Args:
            code (str): The Python code to run
        """
        try:
            self._socket.execute_code(code)
        except Exception as e:
            logger.error(f"Failed to execute code '{code}': {e}")

    def execute_callable(self, func: Callable, *args, **kwargs):
        """Execute a callable in the Blender Python environment.
        Args:
            func (callable): The callable to run
            *args: Positional arguments for the callable
            **kwargs: Keyword arguments for the callable
        """
        try:
            self._socket.execute_callable(func, *args, **kwargs)
        except Exception as e:
            logger.error(f"Failed to execute callable '{func}': {e}")

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

    def _quit_blender(self):
        try:
            logger.info("Quitting Blender...")
            # Send quit command to the socket server
            # Disable the quit confirmation dialog
            bpy.context.preferences.use_save_prompt = False
            bpy.data.is_dirty = False
            bpy.ops.screen.animation_cancel()
            bpy.ops.wm.quit_blender()
        except Exception as e:
            logger.error(f"Failed to quit Blender: {e}")

    def _stop_server(self):
        try:
            logger.info("Stopping Blender server...")
            # Send stop command to the socket server
            self._socket.send_server_request(b"STOP", "CODE")
        except Exception as e:
            logger.error(f"Failed to stop Blender server: {e}")
