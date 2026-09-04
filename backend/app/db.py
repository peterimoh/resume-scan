"""SQLite persistence for users, sessions, profiles and resumes.

A resume belongs to a profile; a profile belongs to a user. The database
file defaults to the repo-root ``resume.db`` used by the original Streamlit
app, so existing data is picked up and migrated in place (see
``init_db``/``migrate_legacy_resumes_for_user``).
"""

from __future__ import annotations

import json
import re
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone

from . import config

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_password_reset_user_id ON password_reset_tokens(user_id);

CREATE TABLE IF NOT EXISTS profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    headline TEXT,
    kind TEXT NOT NULL DEFAULT 'standard',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_profiles_user_id ON profiles(user_id);

CREATE TABLE IF NOT EXISTS resumes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER REFERENCES profiles(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    template TEXT NOT NULL DEFAULT 'classic',
    font TEXT NOT NULL DEFAULT 'lmodern',
    data TEXT NOT NULL,
    pdf BLOB,
    source TEXT NOT NULL DEFAULT 'built',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS generations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resume_id INTEGER NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    job_description TEXT NOT NULL,
    result TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_generations_resume_id ON generations(resume_id);

CREATE TABLE IF NOT EXISTS job_subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    keyword TEXT NOT NULL,
    channel TEXT NOT NULL,
    channel_target TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_job_subs_user ON job_subscriptions(user_id);

CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dedup_hash TEXT NOT NULL UNIQUE,
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    company TEXT,
    location TEXT,
    location_category TEXT NOT NULL DEFAULT 'Unspecified',
    job_type TEXT,
    type_category TEXT NOT NULL DEFAULT 'On-site',
    salary TEXT,
    description TEXT,
    url TEXT NOT NULL,
    posted_at TEXT,
    fetched_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_jobs_dedup ON jobs(dedup_hash);
CREATE INDEX IF NOT EXISTS idx_jobs_fetched_at ON jobs(fetched_at);

CREATE TABLE IF NOT EXISTS job_notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    subscription_id INTEGER REFERENCES job_subscriptions(id) ON DELETE SET NULL,
    channel TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'sent',
    sent_at TEXT NOT NULL,
    UNIQUE(user_id, job_id)
);
CREATE INDEX IF NOT EXISTS idx_notif_user ON job_notifications(user_id);

CREATE TABLE IF NOT EXISTS telegram_connect_tokens (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_telegram_tokens_user_id ON telegram_connect_tokens(user_id);

CREATE TABLE IF NOT EXISTS telegram_links (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    chat_id TEXT NOT NULL,
    username TEXT,
    linked_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    # WAL lets readers proceed while a writer is active instead of locking
    # the whole file, which matters here since every request opens its own
    # short-lived connection under FastAPI's threadpool. NORMAL is safe (not
    # just fast) specifically in WAL mode: SQLite still guarantees the
    # database stays consistent after a crash, it just skips the fsync that
    # FULL would do after every transaction.
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def init_db() -> None:
    with closing(_connect()) as conn, conn:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(_SCHEMA)
        user_cols = [r["name"] for r in conn.execute("PRAGMA table_info(users)")]
        # Google sign-in links an OAuth identity to the account; older
        # databases predate the column.
        if "google_id" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN google_id TEXT")
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(resumes)")]
        # Legacy migration from the pre-multi-user schema, which had no
        # profile_id column; new rows always populate it, but old rows are
        # backfilled lazily on first registration (see
        # migrate_legacy_resumes_for_user below).
        if "profile_id" not in cols:
            conn.execute("ALTER TABLE resumes ADD COLUMN profile_id INTEGER")
        if "font" not in cols:
            conn.execute(
                "ALTER TABLE resumes ADD COLUMN font TEXT NOT NULL DEFAULT 'lmodern'"
            )
        if "source" not in cols:
            conn.execute(
                "ALTER TABLE resumes ADD COLUMN source TEXT NOT NULL DEFAULT 'built'"
            )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_resumes_profile_id ON resumes(profile_id)")
        profile_cols = [r["name"] for r in conn.execute("PRAGMA table_info(profiles)")]
        # 'quick' profiles are a hidden, auto-created bucket for profile-less
        # ATS/HR scans (see get_or_create_quick_profile); older databases
        # predate the column and default every existing profile to 'standard'.
        if "kind" not in profile_cols:
            conn.execute("ALTER TABLE profiles ADD COLUMN kind TEXT NOT NULL DEFAULT 'standard'")
        job_cols = [r["name"] for r in conn.execute("PRAGMA table_info(jobs)")]
        # job_type (e.g. "Full-time · Remote") and salary predate the first
        # ingestion run for databases created before these fields existed.
        if "job_type" not in job_cols:
            conn.execute("ALTER TABLE jobs ADD COLUMN job_type TEXT")
        if "salary" not in job_cols:
            conn.execute("ALTER TABLE jobs ADD COLUMN salary TEXT")
        if "description" not in job_cols:
            conn.execute("ALTER TABLE jobs ADD COLUMN description TEXT")
        if "type_category" not in job_cols:
            # Sources report job_type as messy, source-specific free text
            # (e.g. "Entry, Intern, Full time · Onsite"); type_category is a
            # small normalized facet derived from it, computed once here for
            # pre-existing rows and from then on at ingestion time.
            conn.execute("ALTER TABLE jobs ADD COLUMN type_category TEXT NOT NULL DEFAULT 'On-site'")
            rows = conn.execute("SELECT id, job_type FROM jobs").fetchall()
            conn.executemany(
                "UPDATE jobs SET type_category = ? WHERE id = ?",
                [(categorize_job_type(r["job_type"]), r["id"]) for r in rows],
            )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_type_category ON jobs(type_category)")
        if "location_category" not in job_cols:
            # location is messy, source-specific free text mixing cities,
            # states, countries and region blocs (e.g. "Berlin, Berlin,
            # Deutschland", "Abia State", "EMEA,  LATAM,  USA") — this is a
            # small normalized facet derived from it, computed once here for
            # pre-existing rows and from then on at ingestion time. Mirrors
            # type_category above.
            conn.execute("ALTER TABLE jobs ADD COLUMN location_category TEXT NOT NULL DEFAULT 'Unspecified'")
            rows = conn.execute("SELECT id, location FROM jobs").fetchall()
            conn.executemany(
                "UPDATE jobs SET location_category = ? WHERE id = ?",
                [(categorize_location(r["location"]), r["id"]) for r in rows],
            )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_location_category ON jobs(location_category)")


def has_unclaimed_legacy_resumes() -> bool:
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT 1 FROM resumes WHERE profile_id IS NULL LIMIT 1"
        ).fetchone()
    return row is not None


def migrate_legacy_resumes_for_user(user_id: int) -> None:
    """Attach any pre-multi-user resumes (profile_id IS NULL) to a new
    "Imported" profile owned by ``user_id``. No-op if there is nothing to
    migrate. Intended to run once, right after the first user registers."""
    with closing(_connect()) as conn, conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM resumes WHERE profile_id IS NULL"
        ).fetchone()
        if not row or not row["n"]:
            return
        now = _now()
        cur = conn.execute(
            "INSERT INTO profiles (user_id, name, headline, created_at, updated_at) "
            "VALUES (?, 'Imported', NULL, ?, ?)",
            (user_id, now, now),
        )
        profile_id = cur.lastrowid
        conn.execute(
            "UPDATE resumes SET profile_id = ? WHERE profile_id IS NULL",
            (profile_id,),
        )


def seed_legacy_json_if_empty() -> None:
    """Import the legacy resume.json as an unclaimed (profile_id IS NULL)
    resume row, if the resumes table is otherwise empty. Mirrors the
    original Streamlit app's first-run seeding; the row is picked up by
    migrate_legacy_resumes_for_user on first registration."""
    if not config.LEGACY_JSON_PATH.exists():
        return
    with closing(_connect()) as conn:
        row = conn.execute("SELECT COUNT(*) AS n FROM resumes").fetchone()
        if row and row["n"]:
            return
    try:
        data = json.loads(config.LEGACY_JSON_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(data, dict):
        return
    now = _now()
    with closing(_connect()) as conn, conn:
        conn.execute(
            "INSERT INTO resumes (profile_id, name, template, font, data, pdf, created_at, updated_at) "
            "VALUES (NULL, ?, 'classic', 'lmodern', ?, NULL, ?, ?)",
            (
                data.get("name") or "Imported Resume",
                json.dumps(data, ensure_ascii=False),
                now,
                now,
            ),
        )


# --- Users ------------------------------------------------------------


def create_user(email: str, password_hash: str) -> int:
    with closing(_connect()) as conn, conn:
        cur = conn.execute(
            "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
            (email, password_hash, _now()),
        )
        return cur.lastrowid


def get_user_by_email(email: str) -> dict | None:
    with closing(_connect()) as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict | None:
    with closing(_connect()) as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


# --- Sessions -----------------------------------------------------------


def create_session(user_id: int, token: str) -> str:
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=config.SESSION_MAX_AGE_DAYS)
    with closing(_connect()) as conn, conn:
        conn.execute(
            "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (token, user_id, now.isoformat(timespec="seconds"), expires.isoformat(timespec="seconds")),
        )
    return expires.isoformat(timespec="seconds")


def get_session_user(token: str) -> dict | None:
    """Return the user for a valid, unexpired session token, or None.

    Lazily deletes the session row if it has expired.
    """
    with closing(_connect()) as conn, conn:
        row = conn.execute(
            "SELECT s.token, s.expires_at, u.* FROM sessions s "
            "JOIN users u ON u.id = s.user_id WHERE s.token = ?",
            (token,),
        ).fetchone()
        if row is None:
            return None
        if datetime.fromisoformat(row["expires_at"]) < datetime.now(timezone.utc):
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            return None
        user = dict(row)
        user.pop("token", None)
        user.pop("expires_at", None)
        return user


def delete_session(token: str) -> None:
    with closing(_connect()) as conn, conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))


def delete_user_sessions(user_id: int) -> None:
    """Invalidate every session for a user (used after a password reset)."""
    with closing(_connect()) as conn, conn:
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))


# --- Password resets ----------------------------------------------------


def create_password_reset_token(user_id: int, token_hash: str, expires_at: str) -> None:
    with closing(_connect()) as conn, conn:
        conn.execute(
            "INSERT INTO password_reset_tokens (token_hash, user_id, created_at, expires_at) "
            "VALUES (?, ?, ?, ?)",
            (token_hash, user_id, _now(), expires_at),
        )


def get_password_reset_user_id(token_hash: str) -> int | None:
    """Return the user id for a valid, unexpired reset token, or None.

    Lazily deletes the token row if it has expired.
    """
    with closing(_connect()) as conn, conn:
        row = conn.execute(
            "SELECT user_id, expires_at FROM password_reset_tokens WHERE token_hash = ?",
            (token_hash,),
        ).fetchone()
        if row is None:
            return None
        if datetime.fromisoformat(row["expires_at"]) < datetime.now(timezone.utc):
            conn.execute(
                "DELETE FROM password_reset_tokens WHERE token_hash = ?", (token_hash,)
            )
            return None
        return row["user_id"]


def delete_password_reset_token(token_hash: str) -> None:
    with closing(_connect()) as conn, conn:
        conn.execute("DELETE FROM password_reset_tokens WHERE token_hash = ?", (token_hash,))


# --- Users: Google identity & password updates ----------------------------


def update_user_password(user_id: int, password_hash: str) -> None:
    with closing(_connect()) as conn, conn:
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id)
        )


def get_user_by_google_id(google_id: str) -> dict | None:
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE google_id = ?", (google_id,)
        ).fetchone()
    return dict(row) if row else None


def set_google_id(user_id: int, google_id: str) -> None:
    with closing(_connect()) as conn, conn:
        conn.execute("UPDATE users SET google_id = ? WHERE id = ?", (google_id, user_id))


def create_google_user(email: str, google_id: str, password_hash: str) -> int:
    """Create an account for a Google identity. The password hash is a
    random unusable value — the account signs in via Google, not password."""
    with closing(_connect()) as conn, conn:
        cur = conn.execute(
            "INSERT INTO users (email, password_hash, google_id, created_at) "
            "VALUES (?, ?, ?, ?)",
            (email, password_hash, google_id, _now()),
        )
        return cur.lastrowid


# --- Profiles -------------------------------------------------------------


def create_profile(user_id: int, name: str, headline: str | None = None) -> int:
    now = _now()
    with closing(_connect()) as conn, conn:
        cur = conn.execute(
            "INSERT INTO profiles (user_id, name, headline, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, name, headline, now, now),
        )
        return cur.lastrowid


def list_profiles(user_id: int) -> list[dict]:
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT p.*, (SELECT COUNT(*) FROM resumes r WHERE r.profile_id = p.id) AS resume_count "
            "FROM profiles p WHERE p.user_id = ? AND p.kind = 'standard' ORDER BY p.updated_at DESC",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def find_quick_profile(user_id: int) -> int | None:
    """Look up the id of the hidden 'Quick Scans' profile for ``user_id``
    without creating it. Returns None if the user has never run a
    profile-less scan."""
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT id FROM profiles WHERE user_id = ? AND kind = 'quick'", (user_id,)
        ).fetchone()
    return row["id"] if row else None


def get_or_create_quick_profile(user_id: int) -> int:
    """Return the id of the hidden 'Quick Scans' profile that backs
    profile-less ATS/HR scans, creating it on first use. Never shown in
    list_profiles / the "My profiles" grid (kind != 'standard')."""
    existing = find_quick_profile(user_id)
    if existing is not None:
        return existing
    now = _now()
    with closing(_connect()) as conn, conn:
        cur = conn.execute(
            "INSERT INTO profiles (user_id, name, headline, kind, created_at, updated_at) "
            "VALUES (?, 'Quick Scans', NULL, 'quick', ?, ?)",
            (user_id, now, now),
        )
        return cur.lastrowid


def get_profile(profile_id: int) -> dict | None:
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT p.*, (SELECT COUNT(*) FROM resumes r WHERE r.profile_id = p.id) AS resume_count "
            "FROM profiles p WHERE p.id = ?",
            (profile_id,),
        ).fetchone()
    return dict(row) if row else None


def update_profile(profile_id: int, name: str, headline: str | None) -> None:
    with closing(_connect()) as conn, conn:
        conn.execute(
            "UPDATE profiles SET name = ?, headline = ?, updated_at = ? WHERE id = ?",
            (name, headline, _now(), profile_id),
        )


def delete_profile(profile_id: int) -> None:
    with closing(_connect()) as conn, conn:
        conn.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))


# --- Resumes ----------------------------------------------------------


def list_resumes(profile_id: int) -> list[dict]:
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT id, profile_id, name, template, font, source, created_at, updated_at, "
            "       (pdf IS NOT NULL) AS has_pdf "
            "FROM resumes WHERE profile_id = ? ORDER BY updated_at DESC",
            (profile_id,),
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["has_pdf"] = bool(d["has_pdf"])
        result.append(d)
    return result


def get_resume(resume_id: int) -> dict | None:
    with closing(_connect()) as conn:
        row = conn.execute("SELECT * FROM resumes WHERE id = ?", (resume_id,)).fetchone()
    if row is None:
        return None
    r = dict(row)
    r["data"] = json.loads(r["data"])
    return r


def create_resume(
    profile_id: int, name: str, template: str, font: str, data: dict, pdf: bytes | None = None
) -> int:
    now = _now()
    with closing(_connect()) as conn, conn:
        cur = conn.execute(
            "INSERT INTO resumes (profile_id, name, template, font, data, pdf, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (profile_id, name, template, font, json.dumps(data, ensure_ascii=False), pdf, now, now),
        )
        return cur.lastrowid


def update_resume(resume_id: int, name: str, template: str, font: str, data: dict) -> None:
    with closing(_connect()) as conn, conn:
        conn.execute(
            "UPDATE resumes SET name = ?, template = ?, font = ?, data = ?, updated_at = ? "
            "WHERE id = ?",
            (name, template, font, json.dumps(data, ensure_ascii=False), _now(), resume_id),
        )


def save_pdf(resume_id: int, pdf: bytes) -> None:
    with closing(_connect()) as conn, conn:
        conn.execute(
            "UPDATE resumes SET pdf = ?, updated_at = ? WHERE id = ?",
            (pdf, _now(), resume_id),
        )


def delete_resume(resume_id: int) -> None:
    with closing(_connect()) as conn, conn:
        conn.execute("DELETE FROM resumes WHERE id = ?", (resume_id,))


def create_uploaded_resume(profile_id: int, name: str, pdf: bytes) -> int:
    """Store a user-uploaded PDF as a resume row with no structured data —
    used by the profile-less "Quick Check" flow. Analysis reads its text
    straight off ``pdf`` (see analysis._resume_text), so no LaTeX render or
    compile ever happens for these rows."""
    now = _now()
    with closing(_connect()) as conn, conn:
        cur = conn.execute(
            "INSERT INTO resumes (profile_id, name, template, font, data, pdf, source, created_at, updated_at) "
            "VALUES (?, ?, 'uploaded', '', '{}', ?, 'uploaded', ?, ?)",
            (profile_id, name, pdf, now, now),
        )
        return cur.lastrowid


def duplicate_resume(resume_id: int) -> int | None:
    """Copy a resume's name/template/font/data into a new row under the
    same profile. The compiled PDF is intentionally not carried over, so
    the copy is forced through a fresh compile rather than showing a stale
    PDF for edited content."""
    full = get_resume(resume_id)
    if full is None:
        return None
    return create_resume(
        full["profile_id"],
        f"{full['name']} (copy)",
        full["template"],
        full["font"],
        full["data"],
        pdf=None,
    )


# --- Generations (HR review / ATS check / cover letter history) -----------


def create_generation(resume_id: int, kind: str, job_description: str, result: str) -> int:
    with closing(_connect()) as conn, conn:
        cur = conn.execute(
            "INSERT INTO generations (resume_id, kind, job_description, result, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (resume_id, kind, job_description, result, _now()),
        )
        return cur.lastrowid


def list_generations(resume_id: int, kind: str | None = None) -> list[dict]:
    with closing(_connect()) as conn:
        if kind:
            rows = conn.execute(
                "SELECT id, resume_id, kind, job_description, created_at FROM generations "
                "WHERE resume_id = ? AND kind = ? ORDER BY created_at DESC",
                (resume_id, kind),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, resume_id, kind, job_description, created_at FROM generations "
                "WHERE resume_id = ? ORDER BY created_at DESC",
                (resume_id,),
            ).fetchall()
    return [dict(r) for r in rows]


def list_all_generations(user_id: int, kind: str | None = None) -> list[dict]:
    """Every HR/ATS/cover-letter run for ``user_id``, across every profile
    (including the hidden 'Quick Scans' one), newest first. Backs the
    unified History page so profile-less scans are never orphaned."""
    query = (
        "SELECT g.id, g.resume_id, g.kind, g.job_description, g.created_at, "
        "       r.name AS resume_name, p.id AS profile_id, p.name AS profile_name, "
        "       p.kind AS profile_kind "
        "FROM generations g "
        "JOIN resumes r ON r.id = g.resume_id "
        "JOIN profiles p ON p.id = r.profile_id "
        "WHERE p.user_id = ?"
    )
    params: list = [user_id]
    if kind:
        query += " AND g.kind = ?"
        params.append(kind)
    query += " ORDER BY g.created_at DESC"
    with closing(_connect()) as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def get_generation(generation_id: int) -> dict | None:
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT * FROM generations WHERE id = ?", (generation_id,)
        ).fetchone()
    return dict(row) if row else None


def delete_generation(generation_id: int) -> None:
    with closing(_connect()) as conn, conn:
        conn.execute("DELETE FROM generations WHERE id = ?", (generation_id,))


# --- Job subscriptions --------------------------------------------------


def create_job_subscription(
    user_id: int, keyword: str, channel: str, channel_target: str
) -> int:
    with closing(_connect()) as conn, conn:
        cur = conn.execute(
            "INSERT INTO job_subscriptions (user_id, keyword, channel, channel_target, active, created_at) "
            "VALUES (?, ?, ?, ?, 1, ?)",
            (user_id, keyword, channel, channel_target, _now()),
        )
        return cur.lastrowid


def list_job_subscriptions(user_id: int) -> list[dict]:
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT * FROM job_subscriptions WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_job_subscription(subscription_id: int) -> dict | None:
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT * FROM job_subscriptions WHERE id = ?", (subscription_id,)
        ).fetchone()
    return dict(row) if row else None


def set_job_subscription_active(subscription_id: int, active: bool) -> None:
    with closing(_connect()) as conn, conn:
        conn.execute(
            "UPDATE job_subscriptions SET active = ? WHERE id = ?",
            (1 if active else 0, subscription_id),
        )


def delete_job_subscription(subscription_id: int) -> None:
    with closing(_connect()) as conn, conn:
        conn.execute("DELETE FROM job_subscriptions WHERE id = ?", (subscription_id,))


def list_active_job_subscriptions() -> list[dict]:
    """Every active subscription across all users, joined with the owning
    user's email — used by n8n's match step (GET /internal/subscriptions/active)
    so it doesn't need direct DB access."""
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT s.*, u.email AS user_email FROM job_subscriptions s "
            "JOIN users u ON u.id = s.user_id WHERE s.active = 1"
        ).fetchall()
    return [dict(r) for r in rows]


# --- Jobs -----------------------------------------------------------------


def clean_text(value: str | None) -> str | None:
    """Repair a string that may contain an unpaired UTF-16 surrogate — e.g.
    an emoji truncated mid-codepoint by an upstream source (n8n's JS runs on
    UTF-16 strings; slicing at a fixed character count can split a surrogate
    pair). SQLite's implicit UTF-8 encode — and hashlib — raise
    UnicodeEncodeError on those, so callers should clean text before either
    hashing or storing it."""
    if value is None:
        return None
    return value.encode("utf-8", "replace").decode("utf-8")


def categorize_job_type(job_type: str | None) -> str:
    """Normalize a source's free-text job_type (e.g. "Entry, Intern, Full
    time · Onsite", "Contract · Remote", "berufserfahren · Onsite") into one
    of a small set of facets a user can actually filter by. Employment-type
    keywords take priority over the work-arrangement suffix, since a filter
    for "Internship" or "Contract" is more useful to match on than whether
    that internship/contract happens to be remote."""
    text = (job_type or "").lower()
    if any(k in text for k in ("intern", "trainee", "student")):
        return "Internship"
    if any(k in text for k in ("contract", "freelance", "temporary", "fixed-term", "fixed term")):
        return "Contract"
    if "remote" in text:
        return "Remote"
    return "On-site"


# Exact-match (per comma/semicolon-separated segment) aliases for countries
# and region blocs. Used both to detect a single place (return it) and to
# detect a genuinely multi-country/region posting (2+ distinct matches).
_LOCATION_COUNTRY_ALIASES: dict[str, str] = {
    "usa": "United States", "us": "United States", "united states": "United States",
    "united states of america": "United States",
    "uk": "United Kingdom", "united kingdom": "United Kingdom", "gb": "United Kingdom",
    "england": "United Kingdom", "great britain": "United Kingdom",
    "germany": "Germany", "deutschland": "Germany", "ger": "Germany", "de": "Germany",
    "europe": "Europe",
    "nigeria": "Nigeria", "fct": "Nigeria",
    "canada": "Canada", "mexico": "Mexico", "brazil": "Brazil", "argentina": "Argentina",
    "australia": "Australia", "ireland": "Ireland", "poland": "Poland", "portugal": "Portugal",
    "spain": "Spain", "sweden": "Sweden", "ukraine": "Ukraine", "czechia": "Czechia",
    "czech republic": "Czechia", "romania": "Romania", "singapore": "Singapore",
    "south korea": "South Korea", "japan": "Japan", "pakistan": "Pakistan",
    "philippines": "Philippines", "turkey": "Turkey", "türkiye": "Turkey", "turkiye": "Turkey",
    "uae": "United Arab Emirates", "united arab emirates": "United Arab Emirates",
    "el salvador": "El Salvador", "denmark": "Denmark", "netherlands": "Netherlands",
    "norway": "Norway", "france": "France", "greece": "Greece", "italy": "Italy",
    "india": "India", "ethiopia": "Ethiopia", "rwanda": "Rwanda",
    "apac": "APAC", "emea": "EMEA", "latam": "LATAM",
}

# Substring fallback for bare city/region names that carry no country label
# at all (e.g. "Berlin", "Berlin, Berlin", "Hybrid/München"). Only consulted
# when no segment matched _LOCATION_COUNTRY_ALIASES.
_LOCATION_CITY_ALIASES: dict[str, str] = {
    "münchen": "Germany", "munich": "Germany", "berlin": "Germany", "hamburg": "Germany",
    "cologne": "Germany", "köln": "Germany", "frankfurt": "Germany", "düsseldorf": "Germany",
    "dusseldorf": "Germany", "stuttgart": "Germany", "essen": "Germany", "bremen": "Germany",
    "nürnberg": "Germany", "nuremberg": "Germany", "bielefeld": "Germany", "paderborn": "Germany",
    "neuss": "Germany", "trier": "Germany", "ulm": "Germany", "offenbach": "Germany",
    "garching": "Germany", "salzuflen": "Germany",
    "london": "United Kingdom", "manchester": "United Kingdom", "edinburgh": "United Kingdom",
    "cardiff": "United Kingdom", "leeds": "United Kingdom", "bicester": "United Kingdom",
    "moorgate": "United Kingdom", "cambridge": "United Kingdom",
    "lagos": "Nigeria", "abuja": "Nigeria",
    "sydney": "Australia",
}

_LOCATION_REMOTE_KEYWORDS = ("remote", "anywhere", "worldwide", "home office", "homeoffice", "work from home")


def categorize_location(location: str | None) -> str:
    """Collapse a source's free-text location — a city, a state, a country,
    a region bloc, or a combined list of any of those (e.g. "Berlin,
    Berlin, Deutschland", "Abia State", "EMEA,  LATAM,  Canada,  USA") —
    into a small, consistent facet for filtering. The raw location is still
    stored and shown per-job; this only drives the browse-tab dropdown,
    which previously listed every raw variant as its own option."""
    raw = (location or "").strip()
    if not raw:
        return "Unspecified"

    # A parenthetical is often the clearest signal of all (e.g. "Brunswick
    # (Germany)", "Cologne (GER)") — check its content as its own candidate
    # rather than just stripping it off the segment it's attached to.
    segments = re.split(r",|;|\bor\b|/|&", raw) + re.findall(r"\(([^)]+)\)", raw)
    resolved: set[str] = set()
    for seg in segments:
        seg = re.sub(r"\(.*?\)", "", seg).strip().lower()
        if not seg:
            continue
        for alias, canonical in _LOCATION_COUNTRY_ALIASES.items():
            if re.search(rf"\b{re.escape(alias)}\b", seg):
                resolved.add(canonical)
                break

    if len(resolved) >= 2:
        return "Multiple Countries"
    if len(resolved) == 1:
        return next(iter(resolved))

    low = raw.lower()
    for city, country in _LOCATION_CITY_ALIASES.items():
        if city in low:
            return country
    if raw.rstrip().lower().endswith("state"):
        return "Nigeria"
    if any(k in low for k in _LOCATION_REMOTE_KEYWORDS):
        return "Remote / Worldwide"
    return raw


def upsert_jobs(postings: list[dict]) -> list[dict]:
    """Insert postings not already seen (matched by dedup_hash). Returns
    only the rows that were newly inserted, each with its assigned id, so
    callers only match/notify on genuinely new postings rather than the
    whole feed every run.

    Rows that already exist still get refreshed in place — a re-scraped,
    richer description (e.g. after ingestion stopped truncating text)
    replaces the shorter stored one, and missing salary/location/posted_at
    are filled in — without re-triggering matching or notifications."""
    inserted: list[dict] = []
    now = _now()
    with closing(_connect()) as conn, conn:
        for p in postings:
            job_type = clean_text(p.get("job_type"))
            existing = conn.execute(
                "SELECT id, description, location FROM jobs WHERE dedup_hash = ?", (p["dedup_hash"],)
            ).fetchone()
            if existing is not None:
                new_description = clean_text(p.get("description"))
                old_description = existing["description"]
                if new_description and (not old_description or len(new_description) > len(old_description)):
                    conn.execute(
                        "UPDATE jobs SET description = ? WHERE id = ?",
                        (new_description, existing["id"]),
                    )
                new_location = clean_text(p.get("location"))
                merged_location = existing["location"] or new_location
                conn.execute(
                    "UPDATE jobs SET "
                    "salary = COALESCE(salary, ?), "
                    "location = COALESCE(NULLIF(location, ''), ?), "
                    "location_category = ?, "
                    "posted_at = COALESCE(posted_at, ?) "
                    "WHERE id = ?",
                    (
                        clean_text(p.get("salary")),
                        new_location,
                        categorize_location(merged_location),
                        p.get("posted_at"),
                        existing["id"],
                    ),
                )
                continue
            location = clean_text(p.get("location"))
            cur = conn.execute(
                "INSERT INTO jobs "
                "(dedup_hash, source, title, company, location, location_category, job_type, type_category, salary, description, url, posted_at, fetched_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    p["dedup_hash"],
                    p["source"],
                    clean_text(p["title"]),
                    clean_text(p.get("company")),
                    location,
                    categorize_location(location),
                    job_type,
                    categorize_job_type(job_type),
                    clean_text(p.get("salary")),
                    clean_text(p.get("description")),
                    p["url"],
                    p.get("posted_at"),
                    now,
                ),
            )
            if cur.rowcount:
                row = conn.execute(
                    "SELECT * FROM jobs WHERE id = ?", (cur.lastrowid,)
                ).fetchone()
                inserted.append(dict(row))
    return inserted


def get_job(job_id: int) -> dict | None:
    with closing(_connect()) as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return dict(row) if row else None


def list_jobs(
    q: str | None = None,
    location: str | None = None,
    job_type: str | None = None,
    source: str | None = None,
    posted_within_hours: int | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """Browse the full ingested job pool (not just a user's matches), with
    optional filters. Returns (page of rows, total matching count)."""
    clauses: list[str] = []
    params: list = []
    if q:
        clauses.append("(title LIKE ? OR company LIKE ?)")
        like = f"%{q}%"
        params.extend([like, like])
    if location:
        clauses.append("location_category = ?")
        params.append(location)
    if job_type:
        clauses.append("type_category = ?")
        params.append(job_type)
    if source:
        clauses.append("source = ?")
        params.append(source)
    if posted_within_hours is not None:
        # posted_at is stored as free-form ISO text from each source; SQLite's
        # julianday parses the common variants ("...Z", offsets, date-only).
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=posted_within_hours)).isoformat()
        clauses.append("posted_at IS NOT NULL AND julianday(posted_at) >= julianday(?)")
        params.append(cutoff)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with closing(_connect()) as conn:
        total = conn.execute(f"SELECT COUNT(*) AS n FROM jobs {where}", params).fetchone()["n"]
        rows = conn.execute(
            f"SELECT * FROM jobs {where} ORDER BY fetched_at DESC LIMIT ? OFFSET ?",
            [*params, limit, offset],
        ).fetchall()
    return [dict(r) for r in rows], total


def list_job_filter_options() -> dict:
    """Distinct type_category/source/location_category values actually
    present in the jobs table, so the frontend can render filter dropdowns
    instead of free text. type_category and location_category are both
    normalized facets — see categorize_job_type and categorize_location —
    rather than the raw, source-specific job_type/location strings."""
    with closing(_connect()) as conn:
        job_types = [
            r["type_category"]
            for r in conn.execute("SELECT DISTINCT type_category FROM jobs ORDER BY type_category").fetchall()
        ]
        sources = [
            r["source"] for r in conn.execute("SELECT DISTINCT source FROM jobs ORDER BY source").fetchall()
        ]
        locations = [
            r["location_category"]
            for r in conn.execute(
                "SELECT DISTINCT location_category FROM jobs "
                "WHERE location_category IS NOT NULL AND location_category != '' "
                "ORDER BY location_category"
            ).fetchall()
        ]
    return {"job_types": job_types, "sources": sources, "locations": locations}


# --- Job notifications ------------------------------------------------------


def record_job_notification(
    user_id: int, job_id: int, subscription_id: int | None, channel: str, status: str = "sent"
) -> bool:
    """Insert a notification record. Returns False (no-op) if this user was
    already notified about this job — the UNIQUE(user_id, job_id) constraint
    is the single source of truth for "already notified, don't repeat"."""
    with closing(_connect()) as conn, conn:
        cur = conn.execute(
            "INSERT OR IGNORE INTO job_notifications "
            "(user_id, job_id, subscription_id, channel, status, sent_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, job_id, subscription_id, channel, status, _now()),
        )
        return bool(cur.rowcount)


def list_job_notifications(user_id: int) -> list[dict]:
    """The user's matched-jobs feed: every job they've been notified about,
    newest first — independent of whether external delivery succeeded."""
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT n.id AS notification_id, n.channel, n.status, n.sent_at, j.* "
            "FROM job_notifications n JOIN jobs j ON j.id = n.job_id "
            "WHERE n.user_id = ? ORDER BY n.sent_at DESC",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


# --- Telegram connect flow --------------------------------------------------


def create_telegram_connect_token(user_id: int, token_hash: str, expires_at: str) -> None:
    with closing(_connect()) as conn, conn:
        conn.execute(
            "INSERT INTO telegram_connect_tokens (token_hash, user_id, created_at, expires_at) "
            "VALUES (?, ?, ?, ?)",
            (token_hash, user_id, _now(), expires_at),
        )


def get_telegram_connect_user_id(token_hash: str) -> int | None:
    """Look up and consume a connect token — one-time use regardless of
    whether it was still valid, so a leaked/guessed token can't be replayed
    even after it's expired."""
    with closing(_connect()) as conn, conn:
        row = conn.execute(
            "SELECT user_id, expires_at FROM telegram_connect_tokens WHERE token_hash = ?",
            (token_hash,),
        ).fetchone()
        if row is None:
            return None
        conn.execute("DELETE FROM telegram_connect_tokens WHERE token_hash = ?", (token_hash,))
        if datetime.fromisoformat(row["expires_at"]) < datetime.now(timezone.utc):
            return None
        return row["user_id"]


def set_telegram_link(user_id: int, chat_id: str, username: str | None) -> None:
    with closing(_connect()) as conn, conn:
        conn.execute(
            "INSERT INTO telegram_links (user_id, chat_id, username, linked_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET "
            "chat_id = excluded.chat_id, username = excluded.username, linked_at = excluded.linked_at",
            (user_id, chat_id, username, _now()),
        )


def get_telegram_link(user_id: int) -> dict | None:
    with closing(_connect()) as conn:
        row = conn.execute("SELECT * FROM telegram_links WHERE user_id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def delete_telegram_link(user_id: int) -> None:
    with closing(_connect()) as conn, conn:
        conn.execute("DELETE FROM telegram_links WHERE user_id = ?", (user_id,))
