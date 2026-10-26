import re
import threading

from anima.diagnostics import logger
from anima.utils.subprocess import SubprocessManager


class BlenderOutputMonitor:
    """Monitors Blender process output."""

    def __init__(self, subproc_manager: SubprocessManager):
        self._monitoring: bool = False
        self._thread: threading.Thread = None
        self._subproc_manager = subproc_manager

    def start(self) -> None:
        """Start monitoring process output.
        Args:
            process (subprocess.Popen): The Blender subprocess to monitor.
        """
        process = self._subproc_manager.subprocess
        if not process or not process.stdout:
            return

        self._monitoring = True
        self._thread = threading.Thread(
            target=self._read_stream,
            args=(process.stdout,),  # stderr already merged into stdout
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop monitoring output."""
        logger.debug("Stopping Blender output monitoring thread...")
        self._monitoring = False
        if self._thread:
            self._thread.join(timeout=0.5)

    # Private methods -------------------------------------------------------------------------------------- #

    def _read_stream(self, stream):
        """Read from the stream and output with proper formatting.
        Args:
            stream (io.TextIOWrapper): The stream to read from.
        """
        logger.info("Blender output monitor thread started")
        try:
            while self._monitoring:
                line = stream.readline()
                if not line:  # EOF
                    break
                route_blender_line(line.rstrip())

        except Exception as e:
            if self._monitoring:
                logger.error(f"Error reading output: {e}")
        finally:
            try:
                stream.close()
            except Exception:
                pass


_ANSI = re.compile(r"\x1b\[[0-9;]*m")
# Lines already formatted by Anima's logger inside the Blender process, e.g. "15:41:42.379 INFO ..."
_LOGGED = re.compile(r"^\d{2}:\d{2}:\d{2}\.\d{3} (TRACE|DEBUG|INFO|WARNING|ERROR|CRITICAL)\b")
# Blender's own timestamped lines, e.g. "02:36.777  render           | Saved: ..."
_BLENDER_PREFIX = re.compile(r"^\d{2}:\d{2}\.\d{3}\s+[\w ]+\|\s*")
_QUIET = ("Blender quit", "Saved:", "Blender ")  # start-up banner, shutdown notice and per-frame saves


def route_blender_line(line: str) -> None:
    """Send one line of Blender's output through the logger.

    Lines that Anima's logger already formatted inside Blender are printed unchanged. Anything else (Blender's
    own messages, warnings, tracebacks) is re-logged with an inferred level.

    Args:
        line: The line, without its trailing newline.
    """
    plain = _ANSI.sub("", line).rstrip()
    if not plain.strip():
        return
    if _LOGGED.match(plain):
        print(line)
        return

    text = _BLENDER_PREFIX.sub("", plain)
    if text.startswith(_QUIET):
        logger.debug(f"[blender] {text}")
    elif "WARNING" in text.upper().split("|")[0] or text.upper().startswith("WARNING"):
        logger.warning(f"[blender] {text}")
    elif text.startswith(("Traceback", "  File", "    ")) or re.match(r"^\w*(Error|Exception)\b", text):
        logger.error(f"[blender] {text}")
    else:
        logger.info(f"[blender] {text}")
