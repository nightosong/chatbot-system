"""
Backend logging service.
Provides rotating file logger setup and tail-read helpers for UI log viewer.
"""

import logging
import os
from collections import deque
from logging.handlers import RotatingFileHandler
from typing import List, Optional, Dict, Any


DEFAULT_LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)


def setup_logging(log_dir: str, level: str = "INFO") -> str:
    """
    Configure root logger with console + rotating file handlers.
    Returns absolute log file path.
    """
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.abspath(os.path.join(log_dir, "app.log"))

    log_level = getattr(logging, level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()

    formatter = logging.Formatter(DEFAULT_LOG_FORMAT)

    file_handler = RotatingFileHandler(
        filename=log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Ensure uvicorn logs go through the same handlers
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.propagate = True

    logging.getLogger(__name__).info("Logging initialized. log_file=%s", log_file)
    return log_file


def tail_log_file(
    log_file: str,
    lines: int = 200,
    level: Optional[str] = None,
    contains: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Read tail lines from log file with optional text filters.
    """
    if lines < 1:
        lines = 1
    if lines > 2000:
        lines = 2000

    if not os.path.exists(log_file):
        return {"log_file": log_file, "total": 0, "lines": []}

    level_upper = level.upper() if level else None
    keyword = (contains or "").strip().lower()

    buffer: deque[str] = deque(maxlen=lines * 5)
    with open(log_file, "r", encoding="utf-8", errors="ignore") as file:
        for row in file:
            buffer.append(row.rstrip("\n"))

    filtered: List[str] = []
    for row in buffer:
        if level_upper and f"| {level_upper}" not in row:
            continue
        if keyword and keyword not in row.lower():
            continue
        filtered.append(row)

    tail_lines = filtered[-lines:]
    return {
        "log_file": log_file,
        "total": len(tail_lines),
        "lines": tail_lines,
    }
