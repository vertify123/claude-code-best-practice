"""
Agent Activity Logger
A shared, append-only JSONL log that every Etsy automation script writes to.

Usage (from any script):
  from dashboard.agent_logger import log_event, read_recent, get_agent_statuses

  log_event("etsy-research-agent", "start",    "Scanning 8 niches")
  log_event("etsy-research-agent", "complete", "Top: svg bundle (82pts)")
  log_event("etsy-research-agent", "error",    "API timeout on Etsy search")

Log format (JSONL):
  {"ts": 1705123456.789, "agent": "...", "event": "start|complete|error|info", "detail": "..."}
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Canonical log location — relative to this file's directory
LOG_DIR = Path(__file__).parent / "logs"
LOG_FILE = LOG_DIR / "activity.jsonl"
MAX_LOG_LINES = 2000  # rotate after this many lines


def log_event(agent: str, event: str, detail: str = "") -> None:
    """
    Append one activity entry to the shared log.
    Safe to call from any process — uses line-at-a-time append.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": time.time(),
        "agent": agent,
        "event": event,   # start | complete | error | info
        "detail": detail[:200],  # cap detail length
    }
    with LOG_FILE.open("a") as f:
        f.write(json.dumps(entry) + "\n")

    _maybe_rotate()


def _maybe_rotate() -> None:
    """Keep the log from growing unbounded — trim to last MAX_LOG_LINES."""
    if not LOG_FILE.exists():
        return
    lines = LOG_FILE.read_text().splitlines()
    if len(lines) > MAX_LOG_LINES:
        LOG_FILE.write_text("\n".join(lines[-MAX_LOG_LINES:]) + "\n")


def read_recent(n: int = 50) -> list[dict]:
    """Return the last n log entries, oldest first."""
    if not LOG_FILE.exists():
        return []
    lines = LOG_FILE.read_text().splitlines()
    entries = []
    for line in lines:
        line = line.strip()
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return entries[-n:]


def get_agent_statuses() -> dict[str, dict]:
    """
    Return the most recent log entry per agent.
    Keys: agent name  Values: {status, detail, ts, ago}
    """
    known_agents = [
        "etsy-research-agent",
        "etsy-listing-agent",
        "etsy-customer-service-agent",
        "etsy-analytics-agent",
    ]
    statuses: dict[str, dict] = {
        a: {"status": "idle", "detail": "never run", "ts": 0, "ago": "—"}
        for a in known_agents
    }

    for entry in read_recent(200):
        agent = entry.get("agent", "")
        if agent in statuses and entry["ts"] > statuses[agent]["ts"]:
            ago = _humanize_age(entry["ts"])
            statuses[agent] = {
                "status": entry["event"],
                "detail": entry["detail"],
                "ts": entry["ts"],
                "ago": ago,
            }
    return statuses


def get_json_summary() -> dict:
    """Return a machine-readable summary for the Claude command to display."""
    entries = read_recent(20)
    statuses = get_agent_statuses()
    return {
        "as_of": datetime.now(tz=timezone.utc).isoformat(),
        "agent_statuses": statuses,
        "recent_activity": [
            {
                "time": datetime.fromtimestamp(e["ts"]).strftime("%H:%M:%S"),
                "agent": e["agent"].replace("etsy-", "").replace("-agent", ""),
                "event": e["event"],
                "detail": e["detail"],
            }
            for e in reversed(entries)
        ],
    }


def _humanize_age(ts: float) -> str:
    age = time.time() - ts
    if age < 60:
        return f"{int(age)}s ago"
    elif age < 3600:
        return f"{int(age / 60)}m ago"
    elif age < 86400:
        return f"{int(age / 3600)}h ago"
    else:
        return f"{int(age / 86400)}d ago"


if __name__ == "__main__":
    # Quick test — write a sample event and dump the summary
    log_event("etsy-research-agent", "complete", "Test entry from agent_logger")
    import json as _json
    print(_json.dumps(get_json_summary(), indent=2))
