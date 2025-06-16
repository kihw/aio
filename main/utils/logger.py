from __future__ import annotations

from datetime import datetime
from pathlib import Path


def log_event(message: str, log_path: Path | str | None = None) -> None:
    """Append a timestamped message to the log file."""
    if log_path is None:
        log_path = Path(__file__).resolve().parent.parent / "appflow.log"
    else:
        log_path = Path(log_path)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")
    except Exception:
        # If logging fails, silently ignore to not break workflow
        pass
