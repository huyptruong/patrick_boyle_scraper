"""Tests for extract run logging."""

from __future__ import annotations

from pathlib import Path

from scraper.run_log import log_extract_result


def test_log_extract_result_appends_to_file(tmp_path: Path, monkeypatch) -> None:
    import scraper.config as config
    import scraper.run_log as run_log

    log_path = tmp_path / "run.log"
    monkeypatch.setattr(config, "RUN_LOG_PATH", log_path)
    monkeypatch.setattr(run_log, "_logger", None)

    log_extract_result("abc123", "success", detail="120 chars")
    log_extract_result("def456", "failed", detail="empty clipboard")

    text = log_path.read_text(encoding="utf-8")
    assert "abc123 success 120 chars" in text
    assert "def456 failed empty clipboard" in text
