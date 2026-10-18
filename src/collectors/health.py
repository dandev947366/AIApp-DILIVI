"""Health checks for the MCP job collector.

Consumed by ``app/ui.py::refresh_job_health`` which expects:

    {
        "health": "healthy" | "degraded" | "stale" | "unknown",
        "active_jobs": int,
        "last_successful_run_at": str | None,   # "Never" fallback is UI-side
        "by_country": {country: int, ...},
    }

Probed in order, first responder wins:

    1. SQLite ``jobs`` table in the same DB as the rest of the app
    2. ``DATA_DIR/job_collector_status.json`` (status file)
    3. ``DATA_DIR/jobs.json`` (snapshot: list of job dicts)

Any exception is swallowed and surfaced as ``health="unknown"`` so a
misbehaving collector never crashes Gradio.
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

_DATA_DIR = Path(os.getenv("DATA_DIR", "/app/data"))


# ----------------------------------------------------------------------
# SQLite probe
# ----------------------------------------------------------------------


def _sqlite_path() -> Path | None:
    """Resolve DATABASE_URL → filesystem path."""
    url = os.getenv("DATABASE_URL", "sqlite:///./data/student_context.db")
    for prefix in ("sqlite:///", "sqlite://"):
        if url.startswith(prefix):
            rel = Path(url[len(prefix) :])
            return rel if rel.is_absolute() else Path("/app") / rel
    return None


def _from_sqlite() -> dict[str, Any] | None:
    db = _sqlite_path()
    if db is None or not db.exists():
        return None
    try:
        conn = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
    except sqlite3.Error:
        return None
    try:
        cur = conn.cursor()
        tables = {
            row[0]
            for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }

        jobs_table = next(
            (t for t in ("jobs", "job_listings", "job_postings") if t in tables),
            None,
        )
        if jobs_table is None:
            return None

        cols = {row[1] for row in cur.execute(f"PRAGMA table_info({jobs_table})")}
        active_sql = ""
        if "status" in cols:
            active_sql = "WHERE LOWER(status) = 'active'"
        elif "is_active" in cols:
            active_sql = "WHERE is_active = 1"
        elif "archived" in cols:
            active_sql = "WHERE archived = 0"

        total = cur.execute(
            f"SELECT COUNT(*) FROM {jobs_table} {active_sql}"
        ).fetchone()[0]

        by_country: dict[str, int] = {}
        country_col = next(
            (c for c in ("country", "location_country", "country_code") if c in cols),
            None,
        )
        if country_col:
            for country, count in cur.execute(
                f"SELECT COALESCE({country_col}, 'Unknown'), COUNT(*) "
                f"FROM {jobs_table} {active_sql} "
                f"GROUP BY {country_col} ORDER BY COUNT(*) DESC"
            ):
                by_country[str(country)] = int(count)

        last_run: str | None = None
        for run_table in ("collection_runs", "collector_runs", "job_collector_runs"):
            if run_table not in tables:
                continue
            run_cols = {r[1] for r in cur.execute(f"PRAGMA table_info({run_table})")}
            ts_col = next(
                (
                    c
                    for c in ("finished_at", "completed_at", "created_at")
                    if c in run_cols
                ),
                None,
            )
            if ts_col is None:
                continue
            where = "WHERE LOWER(status) = 'success'" if "status" in run_cols else ""
            row = cur.execute(
                f"SELECT MAX({ts_col}) FROM {run_table} {where}"
            ).fetchone()
            if row and row[0]:
                last_run = str(row[0])
                break

        return {
            "health": "healthy" if total > 0 else "empty",
            "active_jobs": int(total),
            "last_successful_run_at": last_run or "Never",
            "by_country": by_country,
            "source": f"sqlite:{db.name}:{jobs_table}",
        }
    except sqlite3.Error:
        return None
    finally:
        conn.close()


# ----------------------------------------------------------------------
# File probes
# ----------------------------------------------------------------------


def _from_status_file() -> dict[str, Any] | None:
    f = _DATA_DIR / "job_collector_status.json"
    if not f.exists():
        return None
    try:
        data = json.loads(f.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    return {
        "health": data.get("health") or data.get("status") or "unknown",
        "active_jobs": int(data.get("active_jobs") or 0),
        "last_successful_run_at": data.get("last_successful_run_at")
        or data.get("last_run_at")
        or "Never",
        "by_country": dict(data.get("by_country") or {}),
        "source": f"file:{f.name}",
    }


def _from_snapshot() -> dict[str, Any] | None:
    f = _DATA_DIR / "jobs.json"
    if not f.exists():
        return None
    try:
        jobs = json.loads(f.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(jobs, list):
        return None

    active = [
        j
        for j in jobs
        if isinstance(j, dict) and str(j.get("status", "active")).lower() == "active"
    ]
    by_country: dict[str, int] = {}
    for j in active:
        country = j.get("country") or j.get("location") or "Unknown"
        by_country[str(country)] = by_country.get(str(country), 0) + 1

    return {
        "health": "healthy" if active else "empty",
        "active_jobs": len(active),
        "last_successful_run_at": "Never",
        "by_country": by_country,
        "source": f"file:{f.name}",
    }


# ----------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------
# src/collectors/health.py
from sqlalchemy import func
from src.database import SessionLocal
from src.models.job_models import JobModel, JobCollectionRunModel


def get_collection_health() -> dict:
    try:
        with SessionLocal() as db:
            # Count active jobs
            active_jobs = db.query(JobModel).filter(JobModel.is_active == True).count()

            # Get last successful run
            last_run = (
                db.query(JobCollectionRunModel)
                .order_by(JobCollectionRunModel.run_at.desc())
                .first()
            )
            last_run_time = (
                last_run.run_at.strftime("%Y-%m-%d %H:%M:%S") if last_run else "Never"
            )

            # Group by country (Limiting to top 5 so the sidebar doesn't get massive)
            by_country = {}
            if active_jobs > 0:
                results = (
                    db.query(JobModel.country, func.count(JobModel.job_id))
                    .filter(JobModel.is_active == True)
                    .group_by(JobModel.country)
                    .order_by(func.count(JobModel.job_id).desc())
                    .limit(5)
                    .all()
                )
                by_country = {country or "Unknown": count for country, count in results}

            return {
                "health": "healthy" if active_jobs > 0 else "unknown",
                "active_jobs": active_jobs,
                "last_successful_run_at": last_run_time,
                "by_country": by_country,
            }
    except Exception as e:
        return {
            "health": "error",
            "active_jobs": 0,
            "last_successful_run_at": "Error",
            "by_country": {},
        }
