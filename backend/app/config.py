"""App configuration, read from a ``.env`` file in the backend directory
(with environment variables as fallback)."""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"


def _load_env(path: Path) -> dict:
    if not path.exists():
        return {}
    env: dict = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        env[key] = value
    return env


_env = _load_env(ENV_PATH)


def cfg(name: str, default: str = "") -> str:
    return _env.get(name) or os.environ.get(name) or default


# Defaults to the repo-root resume.db (the pre-existing Streamlit app's
# database file) so legacy data is picked up and migrated in place.
DB_PATH = Path(cfg("DB_PATH", str(BASE_DIR.parent / "resume.db")))
SESSION_COOKIE_NAME = "resume_session"
SESSION_MAX_AGE_DAYS = 30
CORS_ORIGINS = [o.strip() for o in cfg("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
COOKIE_SECURE = cfg("COOKIE_SECURE", "false").lower() == "true"

# Legacy single-resume seed file, retained from the original Streamlit app.
LEGACY_JSON_PATH = BASE_DIR.parent / "resume.json"

# --- Auth extras -------------------------------------------------------------

# When set, new-account creation (email/password register and first-time
# Google sign-in) requires this code — share it only with people you invite.
# Leave unset for open registration (fine for a LAN-only deployment).
SIGNUP_CODE = cfg("SIGNUP_CODE")

FRONTEND_URL = cfg("FRONTEND_URL", "http://localhost:5173")
# Public base URL of this backend; used to build the Google OAuth redirect URI.
BACKEND_BASE_URL = cfg("BACKEND_BASE_URL", "http://localhost:8000")

# Google OAuth (sign in with Google). When unset, the /api/auth/google
# endpoint responds with a clear "not configured" error.
GOOGLE_CLIENT_ID = cfg("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = cfg("GOOGLE_CLIENT_SECRET")

# Password reset links expire after this many minutes.
PASSWORD_RESET_TTL_MINUTES = int(cfg("PASSWORD_RESET_TTL_MINUTES", "30"))
# No mailer is wired up yet; while false, forgot-password returns the reset
# token in the API response so the flow is usable in development.
EMAIL_ENABLED = cfg("EMAIL_ENABLED", "false").lower() == "true"

# --- Job board (n8n ingestion) ------------------------------------------

# Shared secret the n8n workflow sends as the X-Internal-Key header on
# every /internal/* call. Unset in dev leaves the internal endpoints
# reachable with no key (fine for localhost-only n8n); set it before
# exposing the backend publicly.
INTERNAL_API_KEY = cfg("INTERNAL_API_KEY")

# --- Telegram connect flow ------------------------------------------------

# From @BotFather when you create the bot.
TELEGRAM_BOT_TOKEN = cfg("TELEGRAM_BOT_TOKEN")
# Bot's @username, without the leading @ — used to build the t.me deep link.
TELEGRAM_BOT_USERNAME = cfg("TELEGRAM_BOT_USERNAME")
# The secret_token you pass to Telegram's setWebhook call; Telegram echoes
# it back on every webhook POST so we can reject spoofed requests. Unset in
# dev skips the check (fine for a localhost tunnel you control).
TELEGRAM_WEBHOOK_SECRET = cfg("TELEGRAM_WEBHOOK_SECRET")
# How long a "connect your Telegram" deep link stays valid.
TELEGRAM_CONNECT_TTL_MINUTES = int(cfg("TELEGRAM_CONNECT_TTL_MINUTES", "10"))
