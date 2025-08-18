import select
import subprocess
import sys
import termios
import threading
import tty

import bpy

from anima.diagnostics import logger
from anima.utils.project import get_main_file_path as main_path
from anima.utils.socket.client import BlenderSocketClient
from anima.utils.subprocess import SubprocessManager


class BlenderInputMonitor:
    def __init__(self, subproc_manager: SubprocessManager):
        self._socket = BlenderSocketClient()
        self._listener_thread = None
        self._stop_listener = threading.Event()
        self._subproc_manager = subproc_manager

    def start(self):
        """Start the hotkey listener thread."""
        if not sys.stdin.isatty():
            logger.warning("stdin not a TTY; hotkey listener disabled")
            return
        self._listener_thread = threading.Thread(
            target=self._listen_for_hotkeys, daemon=True
        )
        self._listener_thread.start()

    def stop(self):
        """Stop the hotkey listener thread."""
        if self._listener_thread and self._listener_thread.is_alive():
            logger.debug("Stopping hotkey listener thread...")
            self._stop_listener.set()
            self._listener_thread.join(timeout=0.5)
            if self._listener_thread.is_alive():
                logger.warning("Listener thread did not stop gracefully")

    def execute(self, func: callable, *args: tuple, **kwargs: dict):
        """Run a callable object in the Blender Python environment.
        Args:
            func (callable): The function to execute.
            *args (tuple): Positional arguments for the function.
            **kwargs (dict): Keyword arguments for the function.
        """
        return self._socket.execute(func, *args, **kwargs)

    def _reload_main(self):
        """Reload the main Anima script."""
        logger.info("Reloading main script...")

        self._blender_to_front()

        def call():
            script_path = main_path()

            # Clear existing handlers to avoid duplicates
            logger.info("Clearing existing handlers...")
            bpy.app.handlers.frame_change_pre.clear()
            bpy.app.handlers.frame_change_post.clear()

            # Execute the script as __main__ so entrypoints run and __file__ is set
            try:
                import runpy

                logger.info("Reloading script: {}", script_path)
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
        self.stop()  # Clean up before quitting
        self._socket.execute(call)

    # Private methods -------------------------------------------------------------------------------------- #

    def _configure_blender(self):
        """Configure Blender settings for Anima."""

        def call():
            prefs = bpy.context.preferences
            prefs.view.ui_scale = 1.25
            prefs.view.show_splash = False  # Hide the splash screen
            prefs.view.show_developer_ui = True  # Show developer extras
            prefs.view.show_tooltips_python = True  # Show tooltips for Python

        self._socket.execute(call)

    def _listen_for_hotkeys(self):
        """Listen for hotkeys in the terminal."""
        logger.info("Hotkey listener thread started. Keyboard shortcuts:")
        logger.info("   Ctrl+R: Reload Anima")
        logger.info("   Ctrl+C: Quit session")
        fd = sys.stdin.fileno()
        old_attrs = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            while not self._stop_listener.is_set():
                if select.select([sys.stdin], [], [], 0.25)[0]:
                    ch = sys.stdin.read(1)
                    if ch == "\x12":  # Ctrl+R
                        self._reload_main()
                    elif ch == "":  # EOF
                        break
        except Exception as e:
            logger.error("Hotkey listener error: {}", e)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_attrs)

    def _blender_to_front(self):
        """Bring the Blender window to the front (Linux only)."""
        if not sys.platform.startswith("linux"):
            raise RuntimeError("Only supported on Linux.")

        process = self._subproc_manager.subprocess
        try:
            # List all windows with their PIDs using wmctrl
            out = subprocess.check_output(["wmctrl", "-lp"]).decode()
        except FileNotFoundError:
            raise RuntimeError("wmctrl not found")

        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 4 and parts[2] == str(process.pid) and "Blender" in line:
                wid = parts[0]
                # Bring the Blender window to the front
                subprocess.run(["wmctrl", "-ia", wid])
                return

        raise RuntimeError(f"No Blender window found for PID {process.pid}")

    def _stop_socket_server(self):
        """Stop the Blender socket server."""
        if not self._socket.stop_server():
            logger.error("Failed to stop Blender socket server")
