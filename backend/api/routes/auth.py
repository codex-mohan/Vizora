"""Authentication routes: register organization + first admin, login, whoami."""

from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import CurrentUser, get_current_user
from core.auth import create_access_token, hash_password, verify_password
from core.database import get_db
from core.models.organization import Organization, User

router = APIRouter()


class RegisterRequest(BaseModel):
    org_name: str
    org_slug: str
    email: str
    password: str
    full_name: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    org_id: str
    role: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    org_id: str
    org_name: str


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new organization with the first admin user."""
    # Check slug uniqueness
    existing = await db.execute(select(Organization).where(Organization.slug == req.org_slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Organization slug already taken")
    
    # Check email uniqueness
    existing = await db.execute(select(User).where(User.email == req.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    org = Organization(name=req.org_name, slug=req.org_slug)
    db.add(org)
    await db.flush()  # get org.id
    
    user = User(
        org_id=org.id,
        email=req.email,
        hashed_password=hash_password(req.password),
        full_name=req.full_name,
        role="admin",
    )
    db.add(user)
    await db.commit()
    await db.refresh(org)
    await db.refresh(user)
    
    token = create_access_token(user.id, org.id, user.role)
    return TokenResponse(
        access_token=token,
        user_id=str(user.id),
        org_id=str(org.id),
        role=user.role,
    )


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login with email + password."""
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")
    
    token = create_access_token(user.id, user.org_id, user.role)
    return TokenResponse(
        access_token=token,
        user_id=str(user.id),
        org_id=str(user.org_id),
        role=user.role,
    )


@router.get("/me", response_model=UserResponse)
async def whoami(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current authenticated user details."""
    result = await db.execute(select(User).where(User.id == current_user.user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get org name
    org_result = await db.execute(select(Organization).where(Organization.id == user.org_id))
    org = org_result.scalar_one_or_none()
    
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name or "",
        role=user.role,
        org_id=str(user.org_id),
        org_name=org.name if org else "",
    )
