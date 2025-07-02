import subprocess
import threading
from anima.diagnostics import logger


class BlenderOutputMonitor:
    """Monitors Blender process output."""

    def __init__(self):
        self._monitoring: bool = False
        self._thread: threading.Thread = None

    def start(self, process: subprocess.Popen) -> None:
        """Start monitoring process output."""
        if not process or not process.stdout:
            return

        self._monitoring = True
        self._thread = threading.Thread(
            target=self._read_stream,
            args=(process.stdout,),
            daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop monitoring output."""
        self._monitoring = False
        if self._thread:
            self._thread.join(timeout=1)  # Don't wait forever

    def _read_stream(self, stream):
        """Read from the stream and output with proper formatting."""
        try:
            while self._monitoring:
                line = stream.readline()
                if not line:  # EOF
                    break

                # Clean the line of control characters and extra whitespace
                cleaned_line = self._clean_line(line)

                if cleaned_line:  # Only log non-empty lines
                    print(f"Blender: {cleaned_line}")
                    # print(cleaned_line)

        except Exception as e:
            if self._monitoring:
                logger.error(f"Error reading output: {e}")
        finally:
            try:
                stream.close()
            except:
                pass

    def _clean_line(self, line: str) -> str:
        """Clean a line of control characters and normalize whitespace."""
        # Remove common control characters
        cleaned = line.replace('\r', '').replace('\b', '')

        # Strip leading/trailing whitespace
        cleaned = cleaned.strip()

        # Replace multiple consecutive spaces with single spaces
        import re
        cleaned = re.sub(r'\s+', ' ', cleaned)

        return cleaned
