import hmac
import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.core.db import prisma

SECRET_KEY = os.getenv("JWT_SECRET", "")
if len(SECRET_KEY) < 32:
    raise RuntimeError("JWT_SECRET must be configured with at least 32 characters.")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(
    data: dict, expires_delta: Optional[timedelta] = None
) -> str:
    to_encode = data.copy()
    to_encode.setdefault("sid", str(uuid4()))
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        session_id = payload.get("sid")
        if (
            not isinstance(email, str)
            or not email
            or not isinstance(session_id, str)
            or not session_id
        ):
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    session = await prisma.authsession.find_unique(where={"id": session_id})
    now = datetime.now(timezone.utc)
    if (
        session is None
        or session.revokedAt is not None
        or session.expiresAt <= now
    ):
        raise credentials_exception

    user = await prisma.user.find_unique(where={"id": session.userId})
    if user is None or not user.isActive or user.email != email:
        raise credentials_exception
    return user


def require_role(roles: list[str]):
    async def role_checker(current_user = Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail="Operation not permitted")
        return current_user
    return role_checker


async def require_agent_token(
    token: Optional[str] = Header(default=None, alias="X-Agent-Token"),
) -> None:
    expected = os.getenv("AGENT_API_TOKEN", "")
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The Windows agent token is not configured.",
        )
    if token is None or not hmac.compare_digest(token, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid agent credentials.",
        )


async def require_agent_or_user(
    agent_token: Optional[str] = Header(default=None, alias="X-Agent-Token"),
    auth_header: Optional[str] = Header(default=None, alias="Authorization"),
):
    """
    Unified authentication dependency for endpoints accessed by both
    machine telemetry agents and authenticated users:
    - Verifies 'X-Agent-Token' using constant-time comparison against AGENT_API_TOKEN.
    - Or verifies 'Authorization: Bearer <JWT>' against active user sessions.
    - Rejects unauthenticated or invalid callers with 401 Unauthorized.
    """
    expected_agent_token = os.getenv("AGENT_API_TOKEN", "")
    if agent_token and expected_agent_token and hmac.compare_digest(agent_token, expected_agent_token):
        return {"type": "agent", "role": "AGENT"}

    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            email = payload.get("sub")
            session_id = payload.get("sid")
            if email and session_id:
                session = await prisma.authsession.find_unique(where={"id": session_id})
                now = datetime.now(timezone.utc)
                if session and session.revokedAt is None and session.expiresAt > now:
                    user = await prisma.user.find_unique(where={"id": session.userId})
                    if user and user.isActive and user.email == email:
                        return user
        except JWTError:
            pass

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer, X-Agent-Token"},
    )
