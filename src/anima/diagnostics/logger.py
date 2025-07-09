import os
import sys
from loguru import logger

LOG_LEVEL = os.getenv("ANIMA_LOG_LEVEL", "DEBUG")
SHOW_FUNCTION = os.getenv("ANIMA_LOG_SHOW_FUNCTION", "0") == "1"
SHOW_PROCESS_INFO = os.getenv("ANIMA_LOG_SHOW_PROCESS_INFO", "0") == "1"


# Configure custom color for log levels
logger.remove()  # Remove default handler
logger.level("INFO", color="<white>")
logger.level("WARNING", color="<bold><yellow>")
logger.level("DEBUG", color="<light-blue>")
logger.level("TRACE", color="<blue>")
logger.level("ERROR", color="<bold><red>")
logger.level("CRITICAL", color="<bold><red>")

# Columns for log formatting
timestamp = "<green>{time:HH:mm:ss.SSS}</green>"
level = "<level>{level: <7}</level>"
proc_id = "<light-blue>{process.id: >5}</light-blue>"
thread_id = "<light-blue>{extra[thread_id_short]: >5}</light-blue>"
func_name = "<light-blue>{function: >26}</light-blue>" if SHOW_FUNCTION else ""
file_name = "<green>{file.name: >25}</green>"
line_number = "<light-green>{line: <3}</light-green>"
message = "<level>{message}</level>"

# Combine columns into a single format string
proc_thread = proc_id + ":" + thread_id if SHOW_PROCESS_INFO else ""
file_line = file_name + ":" + line_number
format = " ".join([timestamp, level, proc_thread,
                  func_name, file_line, message])


def shorten_thread_id(record: dict) -> bool:
    """Add shortened thread ID to record extras"""
    thread_id = record["thread"].id
    record["extra"]["thread_id_short"] = str(thread_id)[-5:].zfill(5)
    return True


# Add structured handler with good formatting
logger.add(
    sys.stderr,
    format=format,
    level=LOG_LEVEL,
    colorize=True,
    backtrace=True,
    diagnose=True,
    filter=shorten_thread_id
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
