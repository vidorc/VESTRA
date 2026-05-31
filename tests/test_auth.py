"""Tests for the auth layer: password hashing, JWT, dependencies, and the
register/login/me flow mounted on a throwaway app with an in-memory Mongo.
"""

from datetime import datetime, timedelta, timezone

import jwt as pyjwt
import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from app.auth.deps import get_current_user_id, require_webhook_key
from app.auth.jwt import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.auth.routes import router as auth_router
from app.config import get_settings
from app.data.mongo import set_client


# --- password hashing ----------------------------------------------------

def test_password_round_trip():
    h = hash_password("correct horse battery staple")
    assert h != "correct horse battery staple"  # not plaintext
    assert h.startswith("pbkdf2_sha256$")
    assert verify_password("correct horse battery staple", h) is True
    assert verify_password("wrong password", h) is False


def test_verify_rejects_malformed_hash():
    assert verify_password("x", "not-a-valid-encoding") is False


def test_two_hashes_of_same_password_differ():
    # Random salt -> different encodings, both verify.
    a = hash_password("samepw")
    b = hash_password("samepw")
    assert a != b
    assert verify_password("samepw", a)
    assert verify_password("samepw", b)


# --- JWT -----------------------------------------------------------------

def test_jwt_round_trip():
    token = create_access_token("user-123")
    payload = decode_access_token(token)
    assert payload["sub"] == "user-123"


def test_expired_token_rejected():
    settings = get_settings()
    expired = pyjwt.encode(
        {
            "sub": "user-123",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        },
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
    with pytest.raises(pyjwt.PyJWTError):
        decode_access_token(expired)


def test_tampered_token_rejected():
    token = create_access_token("user-123")
    with pytest.raises(pyjwt.PyJWTError):
        decode_access_token(token + "x")


# --- dependencies --------------------------------------------------------

async def test_get_current_user_id_missing_token():
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        await get_current_user_id(credentials=None)
    assert exc.value.status_code == 401


async def test_get_current_user_id_valid():
    from fastapi.security import HTTPAuthorizationCredentials

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=create_access_token("u-9"))
    assert await get_current_user_id(credentials=creds) == "u-9"


async def test_webhook_key_correct_and_wrong():
    from fastapi import HTTPException

    good = get_settings().WEBHOOK_API_KEY
    # Correct key -> no exception.
    await require_webhook_key(x_api_key=good)
    # Wrong / missing key -> 401.
    with pytest.raises(HTTPException) as exc:
        await require_webhook_key(x_api_key="nope")
    assert exc.value.status_code == 401
    with pytest.raises(HTTPException):
        await require_webhook_key(x_api_key=None)


# --- end-to-end register / login / me -----------------------------------

@pytest.fixture
async def client():
    set_client(AsyncMongoMockClient())
    app = FastAPI()
    app.include_router(auth_router)

    # A protected probe endpoint to exercise the bearer dependency.
    @app.get("/protected")
    async def protected(user_id: str = Depends(get_current_user_id)):
        return {"user_id": user_id}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    set_client(None)


async def test_register_login_me_flow(client):
    # Register.
    r = await client.post("/auth/register", json={"email": "a@b.com", "password": "supersecret1"})
    assert r.status_code == 201, r.text
    token = r.json()["access_token"]
    uid = r.json()["user_id"]

    # /auth/me with the token.
    r = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json() == {"user_id": uid, "email": "a@b.com"}

    # Login returns a working token for the same user.
    r = await client.post("/auth/login", json={"email": "a@b.com", "password": "supersecret1"})
    assert r.status_code == 200
    assert r.json()["user_id"] == uid


async def test_register_duplicate_email_conflicts(client):
    await client.post("/auth/register", json={"email": "dup@b.com", "password": "supersecret1"})
    r = await client.post("/auth/register", json={"email": "dup@b.com", "password": "supersecret1"})
    assert r.status_code == 409


async def test_login_wrong_password_401(client):
    await client.post("/auth/register", json={"email": "c@b.com", "password": "supersecret1"})
    r = await client.post("/auth/login", json={"email": "c@b.com", "password": "WRONGpassword"})
    assert r.status_code == 401


async def test_protected_requires_token(client):
    r = await client.get("/protected")
    assert r.status_code == 401
    # With a valid token it passes.
    reg = await client.post("/auth/register", json={"email": "d@b.com", "password": "supersecret1"})
    token = reg.json()["access_token"]
    r = await client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
