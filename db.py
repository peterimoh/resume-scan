"""SQLite persistence for saved resumes.

Each row is a single "generation": the full JSON schema of the resume, the
template it was built with, and (optionally) the compiled PDF bytes so it can
be previewed and downloaded without recompiling.

The database file (``resume.db``) lives next to this module.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "resume.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS resumes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    template TEXT NOT NULL DEFAULT 'classic',
    font TEXT NOT NULL DEFAULT 'lmodern',
    data TEXT NOT NULL,
    pdf BLOB,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with closing(_connect()) as conn, conn:
        conn.executescript(_SCHEMA)
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(resumes)")]
        if "font" not in cols:
            conn.execute(
                "ALTER TABLE resumes ADD COLUMN font TEXT NOT NULL DEFAULT 'lmodern'"
            )


def list_resumes() -> list[dict]:
    """Return summary rows for every saved resume, most recently updated first."""
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT id, name, template, font, created_at, updated_at, "
            "       (pdf IS NOT NULL) AS has_pdf "
            "FROM resumes ORDER BY updated_at DESC"
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["has_pdf"] = bool(d["has_pdf"])
        result.append(d)
    return result


def get_resume(resume_id: int) -> dict | None:
    """Return a full resume row with ``data`` parsed and ``pdf`` as bytes."""
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT * FROM resumes WHERE id = ?", (resume_id,)
        ).fetchone()
    if row is None:
        return None
    r = dict(row)
    r["data"] = json.loads(r["data"])
    return r


def create_resume(name: str, template: str, font: str, data: dict, pdf: bytes | None = None) -> int:
    now = _now()
    with closing(_connect()) as conn, conn:
        cur = conn.execute(
            "INSERT INTO resumes (name, template, font, data, pdf, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (name, template, font, json.dumps(data, ensure_ascii=False), pdf, now, now),
        )
        return cur.lastrowid


def update_resume(resume_id: int, name: str, template: str, font: str, data: dict) -> None:
    """Update the name, template, font and data of an existing resume."""
    with closing(_connect()) as conn, conn:
        conn.execute(
            "UPDATE resumes SET name = ?, template = ?, font = ?, data = ?, updated_at = ? "
            "WHERE id = ?",
            (name, template, font, json.dumps(data, ensure_ascii=False), _now(), resume_id),
        )


def save_pdf(resume_id: int, pdf: bytes) -> None:
    """Store the compiled PDF for a resume."""
    with closing(_connect()) as conn, conn:
        conn.execute(
            "UPDATE resumes SET pdf = ?, updated_at = ? WHERE id = ?",
            (pdf, _now(), resume_id),
        )


def delete_resume(resume_id: int) -> None:
    with closing(_connect()) as conn, conn:
        conn.execute("DELETE FROM resumes WHERE id = ?", (resume_id,))
