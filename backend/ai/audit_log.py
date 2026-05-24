"""
Audit Log — HITL traceability.

Append-only JSONL log of every state-changing or sensitive action.
Required by the Linnify challenge "Human in the Loop" constraint — we keep
a record of what the agent proposed, what the human approved, and when.

Format (one JSON object per line):
    {
      "ts":     ISO-8601 UTC timestamp,
      "action": short tag (ingest_extract, ingest_approve, refresh, merge,
                email_draft, status_change, match, linkedin_search),
      "actor":  "agent" | "human" (humans are HR users approving/editing),
      "target": optional candidate name or id,
      "details": free-form dict (sanitized of secrets)
    }
"""
from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_LOG_PATH = BASE_DIR / "data" / "audit.jsonl"
LOG_PATH = Path(os.getenv("AUDIT_LOG_PATH", str(DEFAULT_LOG_PATH)))

_LOCK = threading.Lock()

# Sanitization of accidental secrets before persisting.
_REDACT_KEYS = {"password", "api_key", "token", "secret", "authorization", "ssn"}


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            k: ("***REDACTED***" if k.lower() in _REDACT_KEYS else _sanitize(v))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_sanitize(v) for v in value]
    if isinstance(value, str) and len(value) > 1000:
        return value[:1000] + "…[truncated]"
    return value


def log_action(
    action: str,
    actor: str = "agent",
    target: str | None = None,
    details: dict | None = None,
) -> None:
    """Append a single audit record. Failures are logged but never raised."""
    record = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "action": action,
        "actor": actor,
        "target": target,
        "details": _sanitize(details or {}),
    }
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _LOCK:
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError as e:
        logger.warning("Audit log write failed: %s", e)


def read_audit(limit: int = 100, action_filter: str | None = None) -> list[dict]:
    """Return the most recent `limit` audit entries (newest first)."""
    if not LOG_PATH.exists():
        return []

    entries: list[dict] = []
    try:
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if action_filter and rec.get("action") != action_filter:
                    continue
                entries.append(rec)
    except OSError as e:
        logger.warning("Audit log read failed: %s", e)
        return []

    return list(reversed(entries))[:limit]
