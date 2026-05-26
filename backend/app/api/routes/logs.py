import json
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter

router = APIRouter(prefix="/logs", tags=["logs"])

JSONL_LOGS_DIR = Path(__file__).parent.parent.parent / "logs" / "jsonl"  # adjust to wherever your .log files live

@router.get("/today")
def get_today_logs():
    today = datetime.now(timezone.utc).strftime("%d-%m-%Y")
    log_file = JSONL_LOGS_DIR / f"{today}.log"

    if not log_file.exists():
        return []  # no log file yet today — return empty, not a 404

    entries = []
    with log_file.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue  # skip malformed lines

    # newest first so the feed feels live
    entries.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
    return entries
