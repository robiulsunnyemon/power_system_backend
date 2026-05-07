from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from app.modules.settings import service, schemas
from app.modules.admin.router import get_current_admin
from prisma.enums import SettingType

router = APIRouter(prefix="/settings", tags=["Settings"])

@router.post("/", response_model=schemas.SettingResponse, status_code=status.HTTP_201_CREATED)
async def create_setting(
    data: schemas.SettingCreate,
    admin=Depends(get_current_admin)
):
    """
    Admin only: Create a new setting entry.
    Tittle only:-
      TERMS_CONDITION,
      ABOUT_US,
      PRIVACY_POLICY
    """
    return await service.create_setting(data)

@router.get("/", response_model=List[schemas.SettingResponse])
async def list_settings(
    title: Optional[SettingType] = Query(None, description="Filter by setting title")
):
    """
    Public: List all settings or filter by title.
    """
    return await service.get_settings(title)

@router.get("/{setting_id}", response_model=schemas.SettingResponse)
async def get_setting(setting_id: int):
    """
    Public: Get a specific setting by ID.
    """
    return await service.get_setting_by_id(setting_id)

@router.put("/{setting_id}", response_model=schemas.SettingResponse)
async def update_setting(
    setting_id: int,
    data: schemas.SettingUpdate,
    admin=Depends(get_current_admin)
):
    """
    Admin only: Update an existing setting.
    """
    return await service.update_setting(setting_id, data)

@router.delete("/{setting_id}")
async def delete_setting(
    setting_id: int,
    admin=Depends(get_current_admin)
):
    """
    Admin only: Delete a setting entry.
    """
    return await service.delete_setting(setting_id)
