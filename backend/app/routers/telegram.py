"""Telegram account-linking: a user generates a one-time deep link, opens it
in Telegram, presses Start, and our webhook records the resulting chat_id —
so job-alert subscriptions can target a verified chat instead of asking the
user to go hunt down their own chat ID by hand.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import requests
from fastapi import APIRouter, Depends, Header, HTTPException, status

from .. import config, db, security
from ..deps import get_current_user
from ..schemas import TelegramConnectResponse, TelegramStatusResponse

router = APIRouter(prefix="/api/telegram", tags=["telegram"])


def _send_message(chat_id: str, text: str) -> None:
    """Best-effort confirmation reply — the webhook must return 200 to
    Telegram regardless of whether this succeeds."""
    if not config.TELEGRAM_BOT_TOKEN:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10,
        )
    except requests.exceptions.RequestException:
        pass


@router.post("/connect-token", response_model=TelegramConnectResponse)
def create_connect_token(user: dict = Depends(get_current_user)) -> dict:
    if not config.TELEGRAM_BOT_USERNAME:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telegram isn't configured on this server yet.",
        )
    token = security.new_token()
    expires_at = (
        datetime.now(timezone.utc) + timedelta(minutes=config.TELEGRAM_CONNECT_TTL_MINUTES)
    ).isoformat(timespec="seconds")
    db.create_telegram_connect_token(user["id"], security.hash_token(token), expires_at)
    return {
        "deep_link": f"https://t.me/{config.TELEGRAM_BOT_USERNAME}?start={token}",
        "expires_at": expires_at,
    }


@router.get("/status", response_model=TelegramStatusResponse)
def get_status(user: dict = Depends(get_current_user)) -> dict:
    link = db.get_telegram_link(user["id"])
    if link is None:
        return {"linked": False}
    return {"linked": True, "chat_id": link["chat_id"], "username": link["username"]}


@router.delete("/link", status_code=status.HTTP_204_NO_CONTENT)
def unlink(user: dict = Depends(get_current_user)) -> None:
    db.delete_telegram_link(user["id"])


@router.post("/webhook")
async def webhook(
    body: dict,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict:
    """Telegram POSTs every update sent to the bot here. Always returns
    ``{"ok": True}`` — even for a malformed or irrelevant update — because a
    non-200 response makes Telegram retry the same update indefinitely."""
    if (
        config.TELEGRAM_WEBHOOK_SECRET
        and x_telegram_bot_api_secret_token != config.TELEGRAM_WEBHOOK_SECRET
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook secret")

    message = body.get("message") or {}
    text = (message.get("text") or "").strip()
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    if not text.startswith("/start") or chat_id is None:
        return {"ok": True}

    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        _send_message(str(chat_id), "Open the connect link from the app to link your account.")
        return {"ok": True}

    user_id = db.get_telegram_connect_user_id(security.hash_token(parts[1].strip()))
    if user_id is None:
        _send_message(str(chat_id), "That connect link has expired — generate a new one from the app.")
        return {"ok": True}

    username = chat.get("username") or (message.get("from") or {}).get("username")
    db.set_telegram_link(user_id, str(chat_id), username)
    _send_message(str(chat_id), "Connected! You'll get job alerts here from now on.")
    return {"ok": True}
