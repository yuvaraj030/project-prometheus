"""
Structured Logging Configuration — Fix #7
==========================================
Call `setup_logging()` once at startup. All modules then use:
    import logging
    logger = logging.getLogger(__name__)
"""

import os
import logging
import logging.handlers
from pathlib import Path


def setup_logging(log_dir: str = "logs", log_level: str = None):
    """
    Configure root logger with:
      - Rotating file handler (JSON-structured, 5 MB × 5 backups)
      - Console handler (human-readable, colorized if colorlog installed)

    Args:
        log_dir:   Directory for .log files  (created if missing).
        log_level: Override LOG_LEVEL env var (DEBUG/INFO/WARNING/ERROR).
    """
    level_name = (log_level or os.getenv("LOG_LEVEL", "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)

    Path(log_dir).mkdir(exist_ok=True)
    log_file = os.path.join(log_dir, "agent.log")

    root = logging.getLogger()
    root.setLevel(level)

    # Avoid duplicate handlers on re-import
    if root.handlers:
        return

    fmt_file = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    # --- Rotating file handler ---
    fh = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=5,
        encoding="utf-8",
    )
    fh.setFormatter(fmt_file)
    fh.setLevel(level)
    root.addHandler(fh)

    # --- Console handler (colorized if available) ---
    try:
        import colorlog
        fmt_console = colorlog.ColoredFormatter(
            "%(log_color)s%(levelname)-8s%(reset)s %(cyan)s%(name)s%(reset)s | %(message)s",
            log_colors={
                "DEBUG":    "white",
                "INFO":     "green",
                "WARNING":  "yellow",
                "ERROR":    "red",
                "CRITICAL": "bold_red",
            },
        )
    except ImportError:
        fmt_console = logging.Formatter("%(levelname)-8s %(name)s | %(message)s")

    ch = logging.StreamHandler()
    ch.setFormatter(fmt_console)
    ch.setLevel(level)
    root.addHandler(ch)

    # Silence noisy third-party loggers
    for lib in ["urllib3", "httpx", "httpcore", "asyncio", "uvicorn.access"]:
        logging.getLogger(lib).setLevel(logging.WARNING)

    logging.getLogger("agent").info(
        f"Logging configured: level={level_name}, file={log_file}"
    )
