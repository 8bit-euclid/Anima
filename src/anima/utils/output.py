import subprocess
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
            daemon=True
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
                # Print the raw line for real-time output
                print(line.rstrip())

        except Exception as e:
            if self._monitoring:
                logger.error(f"Error reading output: {e}")
        finally:
            try:
                stream.close()
            except:
                pass
