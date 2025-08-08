import bpy
import keyboard
from anima.diagnostics import logger
from anima.utils.project import get_main_file_path as main_path
from anima.utils.socket.client import BlenderSocketClient


class BlenderInputManager:
    def __init__(self):
        self._socket = BlenderSocketClient()
        # self.setup_hotkeys()

    def setup_hotkeys(self):
        # Set up global hotkeys
        keyboard.add_hotkey('ctrl+r', self.reload_main)
        keyboard.add_hotkey('ctrl+shift+q', self.stop_blender)
        keyboard.add_hotkey('ctrl+shift+s', self.get_status)
        logger.info("Hotkeys registered:")
        logger.info("  Ctrl+R: Reload script")
        logger.info("  Ctrl+Shift+Q: Stop Blender")
        logger.info("  Ctrl+Shift+S: Get status")

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
            script_path = main_path()
            logger.info("Resetting and reloading: {}", script_path)

            # Clear existing handlers to avoid duplicates
            bpy.app.handlers.frame_change_pre.clear()
            bpy.app.handlers.frame_change_post.clear()

            # Execute the script as __main__ so entrypoints run and __file__ is set
            try:
                import runpy
                runpy.run_path(script_path, run_name="__main__")
                logger.info("Script reloaded successfully!")
            except ImportError as e:
                logger.error("Import error during script reload: {}", e)
            except Exception as e:
                logger.error("Unexpected error reloading script: {}", e)

        self._socket.execute(call)

    def quit_blender(self):
        """Quit Blender gracefully."""
        def call():
            bpy.context.preferences.view.use_save_prompt = False
            bpy.ops.screen.animation_cancel()
            bpy.ops.wm.quit_blender()

        logger.info("Quitting Blender...")
        self._socket.execute(call)

    def _stop_socket_server(self):
        """Stop the Blender socket server."""
        if not self._socket.stop_server():
            logger.error("Failed to stop Blender socket server")
