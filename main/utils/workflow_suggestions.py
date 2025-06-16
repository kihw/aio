from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path


LOG_PATH = Path(__file__).resolve().parent.parent / "appflow.log"


def _parse_log(log_path: Path) -> list[tuple[datetime, str]]:
    """Return a list of (timestamp, app_name) for launch events."""
    events: list[tuple[datetime, str]] = []
    if not log_path.exists():
        return events
    pattern = re.compile(r"\[(.*?)\]\s+launch -> (.+)")
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            m = pattern.search(line)
            if not m:
                continue
            ts = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
            app = m.group(2).strip()
            events.append((ts, app))
    return events


def _pair_counts(events: list[tuple[datetime, str]], window: int = 300) -> dict[tuple[str, str], int]:
    """Return counts of appA->appB launches within ``window`` seconds."""
    counts: dict[tuple[str, str], int] = defaultdict(int)
    for (ts_a, app_a), (ts_b, app_b) in zip(events, events[1:]):
        if (ts_b - ts_a).total_seconds() <= window:
            counts[(app_a, app_b)] += 1
    return counts


def generate_suggestions(log_path: Path | None = None, min_count: int = 2) -> list[str]:
    """Analyze logs and return suggestion strings."""
    if log_path is None:
        log_path = LOG_PATH
    events = _parse_log(Path(log_path))
    if not events:
        return []
    counts = _pair_counts(events)
    suggestions: list[str] = []
    for (app_a, app_b), cnt in counts.items():
        if cnt >= min_count:
            suggestions.append(
                f"When '{app_a}' starts, consider launching '{app_b}' automatically (seen {cnt} times)"
            )
    return suggestions


if __name__ == "__main__":
    sugg = generate_suggestions()
    if not sugg:
        print("No suggestions at this time.")
    else:
        print("Suggested workflows:")
        for s in sugg:
            print(f"- {s}")
