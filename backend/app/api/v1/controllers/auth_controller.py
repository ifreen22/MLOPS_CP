from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ALGORITHM,
    SECRET_KEY,
    create_access_token,
    get_current_user,
    oauth2_scheme,
    verify_password,
)
from app.core.db import prisma
from app.core.rate_limit import limiter
from app.schemas.extended import UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


@router.get("/status")
async def auth_status():
    return {"configured": await prisma.user.count() > 0}


@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")
async def login(request: Request, credentials: OAuth2PasswordRequestForm = Depends()):
    user = await prisma.user.find_unique(
        where={"email": credentials.username.strip().lower()}
    )
    if (
        user is None
        or not user.isActive
        or not verify_password(credentials.password, user.passwordHash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    session_id = str(uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    access_token = create_access_token(
        {"sub": user.email, "sid": session_id}
    )
    async with prisma.tx() as transaction:
        await transaction.authsession.create(
            data={
                "id": session_id,
                "userId": user.id,
                "expiresAt": expires_at,
            }
        )
        await transaction.auditlog.create(
            data={
                "organizationId": user.organizationId,
                "userId": user.id,
                "action": "LOGIN",
                "resource": "AuthSession",
                "resourceId": session_id,
            }
        )
    return LoginResponse(
        access_token=access_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user=Depends(get_current_user)):
    return current_user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    token: str = Depends(oauth2_scheme),
    current_user=Depends(get_current_user),
):
    try:
        session_id = jwt.decode(
            token, SECRET_KEY, algorithms=[ALGORITHM]
        )["sid"]
    except (JWTError, KeyError) as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
        ) from error

    async with prisma.tx() as transaction:
        await transaction.authsession.update(
            where={"id": session_id},
            data={"revokedAt": datetime.now(timezone.utc)},
        )
        await transaction.auditlog.create(
            data={
                "organizationId": current_user.organizationId,
                "userId": current_user.id,
                "action": "LOGOUT",
                "resource": "AuthSession",
                "resourceId": session_id,
            }
        )
