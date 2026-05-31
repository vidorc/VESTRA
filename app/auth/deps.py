"""FastAPI auth dependencies.

Two distinct doors:

* ``get_current_user_id`` -- JWT bearer for user-facing endpoints. The user_id is
  derived from the verified token's ``sub`` claim, never from the path/body, so a
  caller can only ever act as themselves.
* ``require_webhook_key`` -- a shared API key (header ``X-API-Key``) for the
  machine-to-machine market-alert webhook, which has no user identity. Fail-closed:
  if ``WEBHOOK_API_KEY`` is unset, every call is rejected.
"""

import hmac

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.jwt import decode_access_token
from app.config import get_settings

_bearer = HTTPBearer(auto_error=False)


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    """Return the authenticated user_id from a valid bearer JWT, else 401."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject.",
        )
    return user_id


async def require_webhook_key(x_api_key: str | None = Header(default=None)) -> None:
    """Authorize the machine-to-machine webhook via shared API key. Fail-closed."""
    configured = get_settings().WEBHOOK_API_KEY
    if not configured or not x_api_key or not hmac.compare_digest(x_api_key, configured):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )


__all__ = ["get_current_user_id", "require_webhook_key"]
