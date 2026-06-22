"""Append-only run log for extract batches."""

from __future__ import annotations

import logging

_logger: logging.Logger | None = None


def _get_logger() -> logging.Logger:
    from config import RUN_LOG_PATH

    global _logger
    if _logger is None:
        RUN_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        _logger = logging.getLogger("patrick_boyle_scraper.extract")
        _logger.setLevel(logging.INFO)
        if not _logger.handlers:
            handler = logging.FileHandler(RUN_LOG_PATH, encoding="utf-8")
            handler.setFormatter(
                logging.Formatter("%(asctime)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
            )
            _logger.addHandler(handler)
    return _logger


def log_extract_result(video_id: str, outcome: str, *, detail: str = "") -> None:
    """Append one line: timestamp, video id, outcome, optional detail."""
    message = f"{video_id} {outcome}"
    if detail:
        message = f"{message} {detail}"
    _get_logger().info(message)
