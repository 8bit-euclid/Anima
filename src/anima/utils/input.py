import bpy
import keyboard
from anima.diagnostics import logger
from anima.utils.project import get_main_file_path as main_path
from anima.utils.socket.client import BlenderSocketClient


class BlenderInputManager:
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

    def execute(self, func: callable, *args: tuple, **kwargs: dict):
        """Run a callable object in the Blender Python environment."""
        return self._socket.execute(func, *args, **kwargs)

    def configure_blender(self):
        def call():
            prefs = bpy.context.preferences
            prefs.view.ui_scale = 1.25
            prefs.view.show_splash = False  # Hide the splash screen
            prefs.view.show_developer_ui = True  # Show developer extras
            prefs.view.show_tooltips_python = True  # Show tooltips for Python

        self._socket.execute(call)

    def reload_main(self):
        def call():
            # bpy.ops.script.reload()
            bpy.ops.script.python_file_run("INVOKE_DEFAULT", main_path())
            # print("main.py" in bpy.data.texts)
        self._socket.execute(call)

    def stop_socket_server(self):
        """Stop the Blender socket server."""
        if not self._socket.stop_server():
            logger.error("Failed to stop Blender socket server")

    def quit_blender(self):
        """Quit Blender gracefully."""
        def call():
            # pcolls = bpy.utils.previews.new()
            # print(f"Preview collections found: {pcolls}")
            # try:
            #     print("Removing preview collection...")
            #     bpy.utils.previews.remove(pcolls)
            # except Exception as e:
            #     print(f"Failed to remove preview collection: {e}")

            bpy.context.preferences.view.use_save_prompt = False
            bpy.ops.screen.animation_cancel()
            bpy.ops.wm.quit_blender()

        logger.info("Quitting Blender...")
        self._socket.execute(call)
