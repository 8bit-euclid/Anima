import os
import sys
from loguru import logger

LOG_LEVEL = os.getenv("ANIMA_LOG_LEVEL", "DEBUG")

# Remove default handler
logger.remove()

# Add structured handler with good formatting
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <5}</level> | <cyan>{file.name}</cyan>: <cyan>{line: <3}</cyan> | <level>{message}</level>",
    level=LOG_LEVEL,
    colorize=True,
    backtrace=True,
    diagnose=True
)
