"""Cron-safe V2 orchestration with one run identity and public failure telemetry."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .export_v2 import DEFAULT_OUTPUT, update_status_export
from .store.v2 import connect_rows, init_v2_schema

LOCK_PATH = Path(__file__).resolve().parent.parent / "data" / "v2-cron.lock"
STALE_LOCK_SECONDS = 12 * 60 * 60
STAGES = (
    ("prefilter", "pipeline.src.v2_prefilter"),
    ("comments", "pipeline.src.hn_comments_v2"),
    ("article", "pipeline.src.sentiment_v2"),
    ("export", "pipeline.src.export_v2"),
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_run(run_id: str, status: str, stage: str, **values: object) -> None:
    conn = connect_rows()
    try:
        with conn:
            existing = conn.execute(
                "SELECT 1 FROM v2_orchestration_runs WHERE run_id = ?", (run_id,),
            ).fetchone()
            if existing:
                assignments = ["status = ?", "stage = ?"] + [f"{name} = ?" for name in values]
                conn.execute(
                    f"UPDATE v2_orchestration_runs SET {', '.join(assignments)} WHERE run_id = ?",
                    [status, stage, *values.values(), run_id],
                )
            else:
                columns = ["run_id", "status", "stage", "started_at", *values]
                placeholders = ", ".join("?" for _ in columns)
                conn.execute(
                    f"INSERT INTO v2_orchestration_runs ({', '.join(columns)}) VALUES ({placeholders})",
                    [run_id, status, stage, now(), *values.values()],
                )
    finally:
        conn.close()


def recover_stale_lock() -> None:
    if not LOCK_PATH.exists():
        return
    age = datetime.now().timestamp() - LOCK_PATH.stat().st_mtime
    if age <= STALE_LOCK_SECONDS:
        raise RuntimeError("A V2 cron run is already active")
    stale_run = f"stale-{uuid.uuid4().hex}"
    write_run(
        stale_run, "failed", "export", finished_at=now(), error_code="STALE_LOCK_RECOVERED",
    )
    LOCK_PATH.unlink()


def counts() -> tuple[int, int, int]:
    conn = connect_rows()
    try:
        discovered = conn.execute(
            "SELECT COUNT(*) FROM v2_prefilter_decisions WHERE eligible = 1"
        ).fetchone()[0]
        articles = conn.execute(
            "SELECT COUNT(DISTINCT hn_story_id) FROM v2_analysis_runs WHERE source = 'article' AND status = 'accepted'"
        ).fetchone()[0]
        comments = conn.execute(
            "SELECT COUNT(*) FROM v2_comment_analyses_normalized WHERE status = 'accepted'"
        ).fetchone()[0]
        return discovered, articles, comments
    finally:
        conn.close()


def run(limit: int | None) -> None:
    init_v2_schema()
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    recover_stale_lock()
    descriptor = os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    run_id = uuid.uuid4().hex
    active_stage = "prefilter"
    try:
        os.write(descriptor, run_id.encode("ascii"))
        write_run(run_id, "running", active_stage)
        for stage, module in STAGES:
            active_stage = stage
            write_run(run_id, "running", stage)
            command = [sys.executable, "-m", module]
            if limit is not None and stage != "export":
                command.extend(["--limit", str(limit)])
            subprocess.run(command, check=True)
        discovered, articles, comments = counts()
        write_run(
            run_id, "succeeded", "export", finished_at=now(),
            stories_discovered=discovered, articles_processed=articles,
            comments_analyzed=comments, error_code=None,
        )
        update_status_export(DEFAULT_OUTPUT)
    except subprocess.CalledProcessError as error:
        write_run(
            run_id, "failed", active_stage,
            finished_at=now(), error_code=f"STAGE_EXIT_{error.returncode}",
        )
        update_status_export(DEFAULT_OUTPUT)
        raise
    finally:
        os.close(descriptor)
        LOCK_PATH.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the scheduled V2 pipeline")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    run(args.limit)


if __name__ == "__main__":
    main()
