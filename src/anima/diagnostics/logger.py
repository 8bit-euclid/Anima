import sys
from loguru import logger

# Remove default handler
logger.remove()

# Add structured handler with good formatting
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <5}</level> | <cyan>{file.name}</cyan>: <cyan>{line: <3}</cyan> | <level>{message}</level>",
    level="TRACE",
    colorize=True,
    backtrace=True,
    diagnose=True
)
