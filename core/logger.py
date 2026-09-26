"""Logging setup — writes to ~/.chatty-chronos/logs/.

Each session gets a timestamped log file.
Errors, tool calls, and LLM interactions are logged.
"""
import logging
import sys
from datetime import datetime
from pathlib import Path

LOG_DIR = Path.home() / ".chatty-chronos" / "logs"


def setup_logger(name: str = "chronos") -> logging.Logger:
    """Create and configure the application logger.
    
    Logs go to both a file (DEBUG level) and stderr (WARNING level).
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = LOG_DIR / f"chronos_{timestamp}.log"

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Avoid duplicate handlers on re-init
    if logger.handlers:
        return logger

    # File handler — everything (DEBUG and up)
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))

    # Console handler — only warnings and errors (to stderr, won't clutter REPL)
    ch = logging.StreamHandler(sys.stderr)
    ch.setLevel(logging.WARNING)
    ch.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))

    logger.addHandler(fh)
    logger.addHandler(ch)

    logger.info("=" * 60)
    logger.info(f"Session started — log file: {log_file}")
    logger.info("=" * 60)

    return logger


# Module-level singleton
log = setup_logger()
