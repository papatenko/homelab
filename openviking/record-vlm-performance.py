#!/usr/bin/env python3
"""Append one redacted OpenViking VLM performance snapshot."""
import datetime as dt
import json
import os
import sqlite3
from pathlib import Path

data_dir = Path(os.environ["OPENVIKING_DATA_DIR"])
db = data_dir / "data" / "_system" / "usage_audit" / "usage_audit.sqlite3"
output = Path(os.environ.get("OPENVIKING_VLM_PERFORMANCE_FILE", data_dir / "metrics" / "vlm-performance.jsonl"))
output.parent.mkdir(parents=True, exist_ok=True)

with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as conn:
    row = conn.execute(
        """SELECT
          COALESCE(SUM(CASE WHEN source='vlm' AND token_type='input' THEN token_count END), 0),
          COALESCE(SUM(CASE WHEN source='vlm' AND token_type='output' THEN token_count END), 0)
        FROM usage_token_hourly WHERE date_utc=date('now')"""
    ).fetchone()
    requests = conn.execute(
        """SELECT status_code, COUNT(*), AVG(duration_ms) FROM request_audit
        WHERE date(created_at)=date('now') GROUP BY status_code"""
    ).fetchall()
    commits = conn.execute(
        """SELECT COALESCE(SUM(count), 0) FROM usage_context_write_bucket
        WHERE date_utc=date('now') AND operation='session.commit'"""
    ).fetchone()[0]

record = {
    "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
    "vlm_input_tokens_today": row[0],
    "vlm_output_tokens_today": row[1],
    "session_commits_today": commits,
    "requests_by_status_today": {
        str(status): {"count": count, "avg_duration_ms": round(duration or 0)}
        for status, count, duration in requests
    },
}
with output.open("a", encoding="utf-8") as f:
    f.write(json.dumps(record, separators=(",", ":")) + "\n")