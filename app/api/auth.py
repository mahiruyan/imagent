from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.security import verify_password
from app.models.user import User
from app.services.audit import record_audit_event

router = APIRouter(tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


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
