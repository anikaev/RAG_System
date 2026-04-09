from __future__ import annotations

import logging

from app.core.request_context import get_current_request_id


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_current_request_id() or "-"
        return True


def configure_logging(log_level: str) -> None:
    root_logger = logging.getLogger()
    level = getattr(logging, log_level.upper(), logging.INFO)

    if root_logger.handlers:
        root_logger.setLevel(level)
        return

    handler = logging.StreamHandler()
    handler.addFilter(RequestIdFilter())
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | %(request_id)s | %(name)s | %(message)s",
        )
    )

    root_logger.setLevel(level)
    root_logger.addHandler(handler)
