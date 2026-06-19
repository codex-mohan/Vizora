"""FastAPI dependencies: authentication, current user, role checks."""

from __future__ import annotations

from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import decode_access_token
from core.database import get_db
from core.models.organization import User

security = HTTPBearer(auto_error=False)


class CurrentUser:
    """Parsed current user from JWT."""
    def __init__(self, user_id: UUID, org_id: UUID, role: str):
        self.user_id = user_id
        self.org_id = org_id
        self.role = role


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    """Extract and validate current user from JWT token."""
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
    user_id = UUID(payload["sub"])
    org_id = UUID(payload["org_id"])
    role = payload["role"]
    
    # Verify user still exists and is active
    result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    
    return CurrentUser(user_id=user_id, org_id=org_id, role=role)


def require_role(*roles: str):
    """Dependency factory: require the current user to have one of the given roles."""
    async def _check(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role: {', '.join(roles)}"
            )
        return current_user
    return _check
