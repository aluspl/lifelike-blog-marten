"""Logs helper for tester CLI

Provides a simple write_log helper that writes to scripts/logs/<name>.log and
returns the path. Creates the logs directory if missing.
"""
from __future__ import annotations
import os
from datetime import datetime


def _logs_dir() -> str:
    dirpath = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(dirpath, exist_ok=True)
    return dirpath


def write_log(name: str, content: str) -> str:
    """Append content to a named log file and return the path."""
    dirpath = _logs_dir()
    filename = f"{name}.log"
    path = os.path.join(dirpath, filename)
    ts = datetime.utcnow().isoformat() + "Z"
    with open(path, "a", encoding="utf8") as f:
        f.write(f"[{ts}] {content}\n")
    return path


def tail_log(name: str, lines: int = 20) -> str:
    """Return the last `lines` lines from the named log file."""
    path = os.path.join(_logs_dir(), f"{name}.log")
    if not os.path.exists(path):
        return ""
    with open(path, encoding="utf8") as f:
        contents = f.read().splitlines()
    return "\n".join(contents[-lines:])
