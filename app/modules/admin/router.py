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

@router.get("/dashboard/stats", response_model=schemas.DashboardStatsResponse)
async def get_stats(admin=Depends(get_current_admin)):
    """
    Admin dashboard: Get user counts and growth percentages.
    """
    return await service.get_dashboard_stats()

@router.get("/dashboard/growth", response_model=schemas.GrowthResponse)
async def get_growth(
    filter: schemas.GrowthFilter = schemas.GrowthFilter.WEEKLY,
    admin=Depends(get_current_admin)
):
    """
    Admin dashboard: Get user growth data points for charts.
    """
    return await service.get_user_growth(filter)
