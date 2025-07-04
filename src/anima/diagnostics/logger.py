import os
import sys
from loguru import logger

LOG_LEVEL = os.getenv("ANIMA_LOG_LEVEL", "DEBUG")

# Remove default handler
logger.remove()

# Configure custom color for log levels
logger.level("INFO", color="<light-blue>")
logger.level("WARNING", color="<bold><yellow>")
logger.level("DEBUG", color="<white>")
logger.level("TRACE", color="<cyan>")
logger.level("ERROR", color="<bold><red>")
logger.level("CRITICAL", color="<bold><red>")

timestamp = "<green>{time:HH:mm:ss.SSS}</green>"
log_level = "<level>{level: <7}</level>"
file_name = "<green>{file.name: >25}</green>"
line_number = "<light-green>{line: <3}</light-green>"
message = "<level>{message}</level>"

# Add structured handler with good formatting
logger.add(
    sys.stderr,
    format=timestamp + " " + log_level + " " +
    file_name + ":" + line_number + " " + message,
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
