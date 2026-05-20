from __future__ import annotations

import secrets

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.services.audit import record_audit_event

router = APIRouter(tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    registration_code: str


@router.post("/login")
async def login(payload: LoginRequest, session: DbSession, request: Request) -> dict[str, str]:
    user = await session.scalar(select(User).where(User.username == payload.username))
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        await record_audit_event(
            session,
            action="login.failed",
            request=request,
            metadata={"username": payload.username},
        )
        await session.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    request.session["user_id"] = str(user.id)
    await record_audit_event(
        session,
        action="login.success",
        request=request,
        actor_id=user.id,
        entity_type="user",
        entity_id=user.id,
    )
    await session.commit()
    return {"status": "ok"}


@router.post("/register")
async def register(payload: RegisterRequest, session: DbSession, request: Request) -> dict[str, str]:
    if not settings.registration_code:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Registration is not configured",
        )
    if not secrets.compare_digest(payload.registration_code, settings.registration_code):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid registration code")

    username = payload.username.strip()
    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    if len(payload.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    existing = await session.scalar(select(User).where(User.username == username))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")

    user = User(
        username=username,
        password_hash=hash_password(payload.password),
        role="operator",
        is_active=True,
    )
    session.add(user)
    await session.flush()
    request.session["user_id"] = str(user.id)
    await record_audit_event(
        session,
        action="user.register",
        request=request,
        actor_id=user.id,
        entity_type="user",
        entity_id=user.id,
    )
    await session.commit()
    return {"status": "ok"}


@router.post("/logout")
async def logout(current_user: CurrentUser, session: DbSession, request: Request) -> dict[str, str]:
    await record_audit_event(
        session,
        action="logout",
        request=request,
        actor_id=current_user.id,
        entity_type="user",
        entity_id=current_user.id,
    )
    request.session.clear()
    await session.commit()
    return {"status": "ok"}


@router.get("/me")
async def me(current_user: CurrentUser) -> dict[str, str]:
    return {
        "id": str(current_user.id),
        "username": current_user.username,
        "role": current_user.role,
    }
