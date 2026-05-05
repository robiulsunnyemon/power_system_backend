from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.modules.admin import service, schemas
from app.modules.users.schemas import UserProfileResponse
from app.common.security import decode_token
from app.core.db import db
from typing import List

router = APIRouter(prefix="/admin", tags=["Admin"])
security = HTTPBearer()

async def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Dependency to verify if the current user has the ADMIN role.
    """
    token = credentials.credentials
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
    user_id = int(payload.get("sub"))
    user = await db.user.find_unique(where={"id": user_id})
    
    if not user or "ADMIN" not in user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Only admins can access this resource"
        )
    
    return user

@router.get("/users", response_model=List[UserProfileResponse])
async def list_users(
    role: schemas.UserRoleFilter = schemas.UserRoleFilter.ALL,
    admin=Depends(get_current_admin)
):
    """
    Endpoint to list all users with role filtering.
    """
    return await service.get_all_users(role)

@router.patch("/users/{user_id}/status", response_model=UserProfileResponse)
async def update_status(
    user_id: int,
    data: schemas.UpdateStatusRequest,
    admin=Depends(get_current_admin)
):
    """
    Endpoint to update a user's account status.
    """
    return await service.update_user_status(user_id, data.accountStatus)
