import datetime
import importlib.resources
import sqlite3
from contextlib import contextmanager

from jobfit.config import DB_PATH


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    schema = importlib.resources.files("jobfit").joinpath("schema.sql").read_text()
    with get_connection() as conn:
        conn.executescript(schema)


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def get_profile() -> sqlite3.Row | None:
    with get_connection() as conn:
        return conn.execute("SELECT * FROM profile WHERE id = 1").fetchone()


def save_profile(cv_filename: str, cv_pdf: bytes, cv_text: str, preferences: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO profile (id, cv_filename, cv_pdf, cv_text, preferences, updated_at)
            VALUES (1, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                cv_filename = excluded.cv_filename,
                cv_pdf = excluded.cv_pdf,
                cv_text = excluded.cv_text,
                preferences = excluded.preferences,
                updated_at = excluded.updated_at
            """,
            (cv_filename, cv_pdf, cv_text, preferences, _now()),
        )


def create_run(model_name: str) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO runs (started_at, status, model_name) VALUES (?, 'running', ?)",
            (_now(), model_name),
        )
        return cursor.lastrowid


def finish_run(
    run_id: int,
    status: str,
    report_markdown: str | None = None,
    error_message: str | None = None,
    log_text: str | None = None,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE runs
            SET finished_at = ?, status = ?, report_markdown = ?, error_message = ?, log_text = ?
            WHERE id = ?
            """,
            (_now(), status, report_markdown, error_message, log_text, run_id),
        )


def save_job_entries(run_id: int, entries: list[dict]) -> None:
    with get_connection() as conn:
        conn.executemany(
            """
            INSERT INTO job_entries
                (run_id, rank, title, company, url, fit_score, apply_decision, rationale, is_rejected)
            VALUES (:run_id, :rank, :title, :company, :url, :fit_score, :apply_decision, :rationale, :is_rejected)
            """,
            [{**entry, "run_id": run_id} for entry in entries],
        )


def list_runs(limit: int = 30) -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()


def get_run(run_id: int) -> sqlite3.Row | None:
    with get_connection() as conn:
        return conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()


def get_latest_run() -> sqlite3.Row | None:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM runs WHERE status = 'success' ORDER BY id DESC LIMIT 1"
        ).fetchone()


def get_job_entries(run_id: int) -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM job_entries WHERE run_id = ? ORDER BY is_rejected, rank", (run_id,)
        ).fetchall()
