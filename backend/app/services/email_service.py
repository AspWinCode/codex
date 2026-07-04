from __future__ import annotations

import logging
import urllib.request
import urllib.error
import json

from app.config import settings

logger = logging.getLogger(__name__)

# Enkod API config
ENKOD_API_URL = "https://api.enkod.ru/v1/mail/"  # trailing slash важен — без него 307 redirect
ENKOD_API_KEY = "p9Q3m6NGZ3KXT9OKOFQt2t5uJQjNs5PmXGj8kbnsBJzg"
ENKOD_WELCOME_MESSAGE_ID = 1470  # messageId для шаблона "логин + пароль"


def _send_enkod(email: str, message_id: int, snippets: dict) -> bool:
    """Send email via Enkod API. Returns True on success."""
    payload = json.dumps({
        "messageId": message_id,
        "email": email,
        "snippets": snippets,
    }).encode("utf-8")

    req = urllib.request.Request(
        ENKOD_API_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "apiKey": ENKOD_API_KEY,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            status_code = resp.getcode()
            logger.info("Enkod response %s for email %s", status_code, email)
            return True
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        logger.error("Enkod HTTP error %s for %s: %s", e.code, email, body)
        return False
    except Exception as e:
        logger.error("Enkod request failed for %s: %s", email, e)
        return False


def send_welcome_email(to: str, login: str, password: str) -> bool:
    """Send login/password to new student via Enkod."""
    return _send_enkod(
        email=to,
        message_id=ENKOD_WELCOME_MESSAGE_ID,
        snippets={"login": login, "password": password},
    )


def send_password_reset_email(to: str, token: str) -> bool:
    """Send password reset link. Uses SMTP fallback if configured, else logs."""
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    logger.info("Password reset link for %s: %s", to, reset_url)
    # Если нужен отдельный Enkod messageId для сброса пароля — добавить сюда
    # return _send_enkod(to, ENKOD_RESET_MESSAGE_ID, {"reset_url": reset_url})
    return False
