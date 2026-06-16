import json
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/logs", tags=["logs"])

JSONL_LOGS_DIR = Path(__file__).parent.parent.parent / "logs" / "jsonl"  # adjust to wherever your .log files live


@router.get("/dates")
def get_available_log_dates():
    """
    Returns a list of available log filenames (date strings, without .log extension),
    sorted newest first.
    """
    if not JSONL_LOGS_DIR.exists():
        return []

    dates = [
        f.stem  # filename without extension, e.g. "16-06-2026"
        for f in JSONL_LOGS_DIR.glob("*.log")
        if f.is_file()
    ]

    # sort newest first — parse as dates since filenames are DD-MM-YYYY
    def parse_date(d: str):
        try:
            return datetime.strptime(d, "%d-%m-%Y")
        except ValueError:
            return datetime.min  # malformed filenames sink to the bottom

    dates.sort(key=parse_date, reverse=True)
    return dates


@router.get("/today")
def get_today_logs():
    today = datetime.now(timezone.utc).strftime("%d-%m-%Y")
    return _read_log_file(today)


@router.get("/{date}")
def get_logs_by_date(date: str):
    """
    Fetch logs for a specific date. Expected format: DD-MM-YYYY (matches filename).
    """
    # basic validation to avoid path traversal / garbage input
    try:
        datetime.strptime(date, "%d-%m-%Y")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Expected DD-MM-YYYY.")

    return _read_log_file(date)


def _read_log_file(date_str: str):
    log_file = JSONL_LOGS_DIR / f"{date_str}.log"

    if not log_file.exists():
        return []

    entries = []
    with log_file.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    entries.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
    return entries
