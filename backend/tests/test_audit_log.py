"""Tests for the append-only audit log."""
import json
from pathlib import Path

import ai.audit_log as audit_log


def _redirect_log(tmp_path: Path, monkeypatch):
    target = tmp_path / "audit.jsonl"
    monkeypatch.setattr(audit_log, "LOG_PATH", target)
    return target


def test_log_action_appends(tmp_path, monkeypatch):
    target = _redirect_log(tmp_path, monkeypatch)
    audit_log.log_action("test_action", actor="human", target="Alice", details={"foo": "bar"})
    audit_log.log_action("test_action", actor="agent")

    lines = target.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert first["action"] == "test_action"
    assert first["actor"] == "human"
    assert first["target"] == "Alice"
    assert first["details"]["foo"] == "bar"
    assert first["ts"].endswith("Z")


def test_secrets_redacted(tmp_path, monkeypatch):
    target = _redirect_log(tmp_path, monkeypatch)
    audit_log.log_action("test", details={"api_key": "sk-leaked", "username": "alice"})

    record = json.loads(target.read_text(encoding="utf-8").strip())
    assert record["details"]["api_key"] == "***REDACTED***"
    assert record["details"]["username"] == "alice"


def test_long_strings_truncated(tmp_path, monkeypatch):
    target = _redirect_log(tmp_path, monkeypatch)
    long_text = "x" * 2000
    audit_log.log_action("test", details={"blob": long_text})

    record = json.loads(target.read_text(encoding="utf-8").strip())
    assert len(record["details"]["blob"]) < 2000
    assert record["details"]["blob"].endswith("[truncated]")


def test_read_audit_newest_first(tmp_path, monkeypatch):
    target = _redirect_log(tmp_path, monkeypatch)
    audit_log.log_action("first")
    audit_log.log_action("second")
    audit_log.log_action("third")

    entries = audit_log.read_audit(limit=10)
    assert [e["action"] for e in entries] == ["third", "second", "first"]


def test_read_audit_filter(tmp_path, monkeypatch):
    _redirect_log(tmp_path, monkeypatch)
    audit_log.log_action("match")
    audit_log.log_action("ingest_approve")
    audit_log.log_action("match")

    matches = audit_log.read_audit(action_filter="match")
    assert len(matches) == 2
    assert all(e["action"] == "match" for e in matches)
