"""Access tokens — header-based, constant-time compared.

Two tokens, two FastAPI dependencies. The chat token guards ``/chat``
(the user pastes it into the frontend gate; it is sent as
``X-Chat-Token`` on every request). The admin token guards ``/admin/*``
(``X-Admin-Token``, never exposed to the browser).

Tokens are loaded from ``.env`` via :mod:`app.config.settings`. If a
configured token is empty, the corresponding dependency rejects every
request — failing closed is the right default. Tests bypass the deps
via ``app.dependency_overrides[...]``.
"""

import hmac

from fastapi import Header, HTTPException, status

from app.config import settings


def _verify(*, supplied: str | None, expected: str | None, what: str) -> None:
    if not expected:
        # Server is misconfigured — no token set. Fail closed; never run open.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{what} not configured on the server",
        )
    if not supplied or not hmac.compare_digest(supplied, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"invalid {what}",
        )


async def require_chat_token(x_chat_token: str | None = Header(default=None)) -> None:
    """FastAPI dependency: validate the X-Chat-Token header against
    ``settings.chat_access_token``.
    """
    _verify(
        supplied=x_chat_token,
        expected=settings.chat_access_token,
        what="chat token",
    )


async def require_admin_token(x_admin_token: str | None = Header(default=None)) -> None:
    """FastAPI dependency: validate the X-Admin-Token header against
    ``settings.admin_token``.
    """
    _verify(
        supplied=x_admin_token,
        expected=settings.admin_token,
        what="admin token",
    )


__all__ = ["require_admin_token", "require_chat_token"]
