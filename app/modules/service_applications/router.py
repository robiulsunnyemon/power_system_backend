from fastapi import APIRouter, Depends, Query, Path, HTTPException,status
from typing import List, Optional
from app.modules.service_applications.schemas import (
    ServiceApplicationCreate, ServiceApplicationResponse, ServiceApplicationStatusUpdate,
    ProviderEarningsResponse
)
from app.modules.service_applications.service import (
    apply_for_service, get_service_applications, get_client_applications, update_application_status,
    get_provider_earnings,get_user_earnings
)
from app.modules.users.router import get_current_user_id
from app.core.db import db
from prisma.enums import Role, ApplicationStatus

router = APIRouter(prefix="/service-applications", tags=["Service Applications"])

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


async def check_user_role(user_id: int = Depends(get_current_user_id)):
    """
    Dependency to verify if the user has the SERVICE_PROVIDER role.
    """
    user = await db.user.find_unique(where={"id": user_id})
    if not user or Role.USER not in user.roles:
        raise HTTPException(
            status_code=403,
            detail="Only User can perform this action"
        )
    return user_id


@router.post("/{service_id}", response_model=ServiceApplicationResponse,status_code=status.HTTP_201_CREATED)
async def apply_service_endpoint(
    data: ServiceApplicationCreate,
    service_id: int = Path(..., title="ID of the service to apply for"),
    client_id: int = Depends(get_current_user_id)
):
    return await apply_for_service(client_id, service_id, data)

@router.get("/my-applications", response_model=List[ServiceApplicationResponse])
async def get_my_applications_endpoint(
    client_id: int = Depends(get_current_user_id)
):
    return await get_client_applications(client_id)

@router.get("/provider/requests", response_model=List[ServiceApplicationResponse])
async def get_provider_requests_endpoint(
    service_id: Optional[int] = Query(None, description="Filter requests by a specific service"),
    status: ApplicationStatus = Query(ApplicationStatus.PENDING, description="Filter requests by status (PENDING, ACCEPTED, DECLINED, COMPLETED)"),
    provider_id: int = Depends(check_provider_role)
):
    return await get_service_applications(provider_id, service_id, status)

@router.patch("/provider/requests/{application_id}/status", response_model=ServiceApplicationResponse)
async def update_request_status_endpoint(
    data: ServiceApplicationStatusUpdate,
    application_id: int = Path(..., title="ID of the application to update"),
    provider_id: int = Depends(check_provider_role)
):
    return await update_application_status(provider_id, application_id, data)

@router.get("/provider/earnings", response_model=ProviderEarningsResponse)
async def get_my_earnings_endpoint(
    provider_id: int = Depends(check_provider_role)
):
    """
    Endpoint for service providers to view their earnings stats and history.
    """
    return await get_provider_earnings(provider_id)



@router.get("/user/total/earnings", response_model=ProviderEarningsResponse)
async def get_my_earnings_endpoint(
    user_id: int = Depends(check_user_role)
):
    """
    Endpoint for user to view their earnings stats and history.
    """
    return await get_user_earnings(user_id)