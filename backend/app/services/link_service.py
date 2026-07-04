from __future__ import annotations

import secrets


def generate_token(task_id: int, user_id: int) -> str:
    """Generate a cryptographically secure URL-safe token (256 bits of entropy)."""
    return secrets.token_urlsafe(32)
