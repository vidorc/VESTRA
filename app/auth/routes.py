"""Auth routes: register, login, me.

Mounted under ``/auth`` by ``app/main.py``. Registration creates a user account
(PBKDF2-hashed password) plus a default investor profile; login returns a signed
JWT; ``/auth/me`` echoes the authenticated identity.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from app.auth.deps import get_current_user_id
from app.auth.jwt import create_access_token, hash_password, verify_password
from app.data.repository import create_user, get_user_by_email, get_user_by_id

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str


class MeResponse(BaseModel):
    user_id: str
    email: str


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest) -> TokenResponse:
    result = await create_user(str(req.email), hash_password(req.password))
    if "error" in result:
        # Email-taken is a client error; anything else is a 500.
        if result["error"] == "Email already registered":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=result["error"])
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not create user.")
    token = create_access_token(result["user_id"])
    return TokenResponse(access_token=token, user_id=result["user_id"])


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest) -> TokenResponse:
    user = await get_user_by_email(str(req.email))
    # Verify even when the user is missing to avoid leaking which emails exist.
    stored = user.get("password_hash", "") if user else ""
    if not user or not verify_password(req.password, stored):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    token = create_access_token(user["user_id"])
    return TokenResponse(access_token=token, user_id=user["user_id"])


@router.get("/me", response_model=MeResponse)
async def me(user_id: str = Depends(get_current_user_id)) -> MeResponse:
    user = await get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return MeResponse(user_id=user["user_id"], email=user["email"])


__all__ = ["router"]
