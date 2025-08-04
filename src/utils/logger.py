import logging
import os
import warnings

from colorlog import ColoredFormatter


def setup_logging():
    log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    formatter = ColoredFormatter(
        fmt=(
            "%(log_color)s[%(asctime)s] "
            "%(levelname)-8s "
            "%(name)s.%(funcName)s:%(lineno)d"
            "%(reset)s - %(message)s"
        ),
        datefmt="%Y-%m-%d %H:%M:%S",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "bold_red,bg_white",
        },
        secondary_log_colors={},
        style="%",
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(log_level)
    root_logger.addHandler(handler)

    logging.captureWarnings(True)

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        log = logging.getLogger(name)
        log.handlers.clear()
        log.setLevel(log_level)
        log.propagate = False
        log.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(logging.NOTSET)
        logger.propagate = True

    return logger
