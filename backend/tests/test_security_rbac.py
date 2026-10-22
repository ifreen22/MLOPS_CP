import pytest
import hmac
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4
from jose import jwt
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core import auth as auth_core
from app.core.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
    require_role,
    require_agent_token,
    require_agent_or_user,
    SECRET_KEY,
    ALGORITHM
)
from app.main import app

client = TestClient(app)


def test_password_hashing():
    pw = "SuperSecurePassword123!"
    h = get_password_hash(pw)
    assert h != pw
    assert verify_password(pw, h) is True
    assert verify_password("WrongPassword123!", h) is False


def test_token_creation_and_decoding():
    payload = {"sub": "alice@sentinel.local", "role": "OPERATOR"}
    token = create_access_token(payload, expires_delta=timedelta(minutes=15))
    decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert decoded["sub"] == "alice@sentinel.local"
    assert decoded["role"] == "OPERATOR"
    assert "sid" in decoded
    assert "exp" in decoded


@pytest.mark.asyncio
async def test_get_current_user_valid(monkeypatch):
    sid = str(uuid4())
    token = create_access_token({"sub": "bob@sentinel.local", "sid": sid})

    mock_session = SimpleNamespace(
        id=sid,
        userId="user-bob",
        revokedAt=None,
        expiresAt=datetime.now(timezone.utc) + timedelta(minutes=10)
    )
    mock_user = SimpleNamespace(
        id="user-bob",
        email="bob@sentinel.local",
        isActive=True,
        role="OPERATOR"
    )

    class MockAuthSession:
        async def find_unique(self, **kwargs):
            return mock_session

    class MockUser:
        async def find_unique(self, **kwargs):
            return mock_user

    monkeypatch.setattr(auth_core, "prisma", SimpleNamespace(authsession=MockAuthSession(), user=MockUser()))

    user = await get_current_user(token=token)
    assert user.id == "user-bob"
    assert user.email == "bob@sentinel.local"


@pytest.mark.asyncio
async def test_get_current_user_revoked_session(monkeypatch):
    sid = str(uuid4())
    token = create_access_token({"sub": "bob@sentinel.local", "sid": sid})

    mock_session = SimpleNamespace(
        id=sid,
        userId="user-bob",
        revokedAt=datetime.now(timezone.utc),
        expiresAt=datetime.now(timezone.utc) + timedelta(minutes=10)
    )

    class MockAuthSession:
        async def find_unique(self, **kwargs):
            return mock_session

    monkeypatch.setattr(auth_core, "prisma", SimpleNamespace(authsession=MockAuthSession()))

    with pytest.raises(HTTPException) as exc:
        await get_current_user(token=token)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_invalid_token():
    with pytest.raises(HTTPException) as exc:
        await get_current_user(token="malformed.jwt.token")
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_require_role_rbac():
    admin_checker = require_role(["ADMIN"])
    operator_checker = require_role(["ADMIN", "OPERATOR"])

    admin_user = SimpleNamespace(role="ADMIN")
    operator_user = SimpleNamespace(role="OPERATOR")
    viewer_user = SimpleNamespace(role="VIEWER")

    assert await admin_checker(admin_user) == admin_user
    assert await operator_checker(admin_user) == admin_user

    assert await operator_checker(operator_user) == operator_user
    with pytest.raises(HTTPException) as exc:
        await admin_checker(operator_user)
    assert exc.value.status_code == 403

    with pytest.raises(HTTPException):
        await admin_checker(viewer_user)
    with pytest.raises(HTTPException):
        await operator_checker(viewer_user)


@pytest.mark.asyncio
async def test_require_agent_token_validation(monkeypatch):
    monkeypatch.setenv("AGENT_API_TOKEN", "secret-agent-token-xyz")

    await require_agent_token(token="secret-agent-token-xyz")

    with pytest.raises(HTTPException) as exc1:
        await require_agent_token(token="wrong-token")
    assert exc1.value.status_code == 401

    monkeypatch.setenv("AGENT_API_TOKEN", "")
    with pytest.raises(HTTPException) as exc2:
        await require_agent_token(token="any-token")
    assert exc2.value.status_code == 503


@pytest.mark.asyncio
async def test_require_agent_or_user_dependency(monkeypatch):
    monkeypatch.setenv("AGENT_API_TOKEN", "agent-token-123")

    res_agent = await require_agent_or_user(agent_token="agent-token-123", auth_header=None)
    assert res_agent["type"] == "agent"
    assert res_agent["role"] == "AGENT"

    sid = str(uuid4())
    token = create_access_token({"sub": "admin@local", "sid": sid})
    mock_session = SimpleNamespace(id=sid, userId="u1", revokedAt=None, expiresAt=datetime.now(timezone.utc)+timedelta(hours=1))
    mock_user = SimpleNamespace(id="u1", email="admin@local", isActive=True, role="ADMIN")

    class MockAuthSession:
        async def find_unique(self, **kwargs):
            return mock_session

    class MockUser:
        async def find_unique(self, **kwargs):
            return mock_user

    monkeypatch.setattr(auth_core, "prisma", SimpleNamespace(authsession=MockAuthSession(), user=MockUser()))

    res_user = await require_agent_or_user(agent_token=None, auth_header=f"Bearer {token}")
    assert res_user.email == "admin@local"

    with pytest.raises(HTTPException) as exc:
        await require_agent_or_user(agent_token=None, auth_header=None)
    assert exc.value.status_code == 401


def test_security_middleware_headers():
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert "Strict-Transport-Security" in res.headers
    assert res.headers["X-Content-Type-Options"] == "nosniff"
    assert res.headers["X-Frame-Options"] == "DENY"
    assert res.headers["Content-Security-Policy"] == "default-src 'self'"
    assert "X-Correlation-ID" in res.headers
