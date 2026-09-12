"""Shared API dependencies: authentication for protected routes."""

from fastapi import Depends, HTTPException, Request, status
from fastapi.security.utils import get_authorization_scheme_param
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def _token_from_request(request: Request) -> str | None:
    """HttpOnly cookie first, ``Authorization: Bearer`` fallback for API clients."""
    cookie_token = request.cookies.get(settings.auth_cookie_name)
    if cookie_token:
        return cookie_token
    authorization = request.headers.get("Authorization")
    if authorization:
        scheme, token = get_authorization_scheme_param(authorization)
        if scheme.lower() == "bearer" and token:
            return token
    return None


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Dependency that rejects unauthenticated requests with 401."""
    token = _token_from_request(request)
    if token is None:
        raise _unauthorized("Not authenticated")
    user_id = decode_access_token(token)
    if user_id is None:
        raise _unauthorized("Invalid or expired session")
    user = db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise _unauthorized("Invalid or expired session")
    return user
