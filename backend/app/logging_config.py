import json
import logging
import uuid

from datetime import datetime, timezone
from pathlib import Path


JSONL_LOGS_DIR = Path(__file__).parent.parent / "app" / "logs" / "jsonl"
JSONL_LOGS_DIR.mkdir(exist_ok=True)
TIMEZONE = timezone.utc


class JsonlRotatingHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self._current_date = self._get_date()
        self._filepath = self._get_filepath()

    def _get_date(self) -> str:
        return datetime.now(tz=TIMEZONE).strftime("%d-%m-%Y")

    def _get_filepath(self) -> str:
        return str(JSONL_LOGS_DIR / f"{self._get_date()}.log")

    def emit(self, record: logging.LogRecord):
        try:
            today = self._get_date()
            if today != self._current_date:
                # Date changed — update path, no rollover machinery needed
                self._current_date = today
                self._filepath = self._get_filepath()

            with open(self._filepath, "a", encoding="utf-8") as f:
                f.write(record.getMessage() + "\n")
        except Exception:
            self.handleError(record)


def get_jsonl_logger() -> logging.Logger:
    """
    Returns a dedicated logger that writes structured JSONL entries
    to a daily rotating file (DD-MM-YYYY.log) in the jsonl logs directory.

    Usage:
        from logging_config import get_jsonl_logger, build_jsonl_entry

        jsonl_logger = get_jsonl_logger()
        jsonl_logger.info(build_jsonl_entry(
            action_type="Export Unleashed",
            action_variant="export-unleashed",
            status="Success",
            message="Exported 212 purchase orders to Unleashed ERP.",
        ))
    """
    logger_name = "jsonl"
    logger = logging.getLogger(logger_name)

    # Avoid adding duplicate handlers if called multiple times
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    logger.propagate = False  # don't bubble up to root logger

    handler = JsonlRotatingHandler()
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    return logger


def build_jsonl_entry(
    action_type: str,
    action_variant: str,
    status: str,
    message: str,
) -> str:
    """
    Builds a JSON string representing one log entry.

    Args:
        action_type:    Human-readable action label e.g. "Export Unleashed"
        action_variant: Machine-readable slug e.g. "export-unleashed"
        status:         "Success", "Failed", "Pending", etc.
        message:        Descriptive message for this log entry

    Returns:
        A JSON string ready to be passed to the jsonl logger.
    """
    entry = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(tz=TIMEZONE).isoformat(),
        "actionType": action_type,
        "actionVariant": action_variant,
        "status": status,
        "message": message,
    }
    return json.dumps(entry)
