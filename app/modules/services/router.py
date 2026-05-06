
from fastapi import APIRouter, Depends, Query, Path, HTTPException,status
from typing import List
from app.modules.services.schemas import ServiceCreate, ServiceUpdate, ServiceResponse, ServiceListResponse
from app.modules.services.service import (
    create_service, get_provider_services, get_all_services, update_service, delete_service
)
from app.modules.users.router import get_current_user_id
from app.core.db import db
from prisma.enums import Role

router = APIRouter(prefix="/services", tags=["Services"])

async def check_provider_role(user_id: int = Depends(get_current_user_id)):
    """
    Dependency to verify if the user has the SERVICE_PROVIDER role.
    """
    user = await db.user.find_unique(where={"id": user_id})
    if not user or Role.SERVICE_PROVIDER not in user.roles:
        raise HTTPException(
            status_code=403, 
            detail="Only service providers can perform this action"
        )
    return user_id

@router.post("/", response_model=ServiceResponse,status_code=status.HTTP_201_CREATED)
async def create_service_endpoint(
    data: ServiceCreate,
    provider_id: int = Depends(check_provider_role)
):
    return await create_service(provider_id, data)

@router.get("/my-services", response_model=ServiceListResponse,status_code=status.HTTP_200_OK)
async def get_my_services_endpoint(
    status: str = Query("ALL", description="Filter by status (ALL, DRAFT, PUBLISHED, etc.)"),
    provider_id: int = Depends(check_provider_role)
):
    return await get_provider_services(provider_id, status)

@router.get("/", response_model=List[ServiceResponse],status_code=status.HTTP_200_OK)
async def get_all_services_endpoint(
    category: str = Query("ALL", description="Filter by category name")
):
    return await get_all_services(category)

@router.patch("/{service_id}", response_model=ServiceResponse,status_code=status.HTTP_200_OK)
async def update_service_endpoint(
    data: ServiceUpdate,
    service_id: int = Path(..., title="The ID of the service to update"),
    provider_id: int = Depends(check_provider_role)
):
    return await update_service(provider_id, service_id, data)

@router.delete("/{service_id}",status_code=status.HTTP_200_OK)
async def delete_service_endpoint(
    service_id: int = Path(..., title="The ID of the service to delete"),
    provider_id: int = Depends(check_provider_role)
):
    return await delete_service(provider_id, service_id)
