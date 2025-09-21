"""
Logging configuration for PDF Prodigy API
"""

import sys
from loguru import logger
from app.core.config import settings

# Remove default logger
logger.remove()

# Add console logger with custom format
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level=settings.LOG_LEVEL,
    colorize=True,
    backtrace=True,
    diagnose=True,
)

# Add file logger for production
if not settings.DEBUG:
    logger.add(
        "logs/pdfprodigy_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="30 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        compression="zip",
    )

# Export logger instance
__all__ = ["logger"]
