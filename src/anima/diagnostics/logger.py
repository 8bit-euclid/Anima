import os
import sys
from loguru import logger

LOG_LEVEL = os.getenv("ANIMA_LOG_LEVEL", "DEBUG")

# Remove default handler
logger.remove()

timestamp = "<green>{time:HH:mm:ss.SSS}</green>"
log_level = "<level>{level: <5}</level>"
file_name = "<cyan>{file.name: <25}</cyan>"
line_number = "<cyan>{line: <3}</cyan>"
message = "<level>{message}</level>"

# Add structured handler with good formatting
logger.add(
    sys.stderr,
    format=timestamp + " | " + log_level + " | " +
    file_name + " | " + line_number + " | " + message,
    level=LOG_LEVEL,
    colorize=True,
    backtrace=True,
    diagnose=True
)


def format_output(title: str, output: str) -> str:
    """Format the output string with a title and the content.
    Args:
        title (str): The title of the output.
        output (str): The content to format.
    Returns:
        str: The formatted output string.
    """
    return f"{title}:\n\n{output}\n"
