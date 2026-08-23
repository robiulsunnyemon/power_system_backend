
from fastapi import APIRouter, Depends, Query, Path, HTTPException,status, UploadFile, File
from typing import List, Optional
from app.modules.services.schemas import (
    ServiceCreate, ServiceUpdate, ServiceResponse, ServiceListResponse,
    PaginatedServiceResponse, ServiceCategoryListResponse, ProviderServicesResponse,
    ServiceCreationPaymentResponse
)
from app.modules.products.schemas import ImageUploadResponse
from app.modules.services.service import (
    create_service, confirm_service_payment, get_provider_services, get_all_services,
    update_service, delete_service, get_service_by_id, get_published_service_categories,
    search_services, upload_service_images
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

@router.post("/upload-images", response_model=ImageUploadResponse)
async def upload_images_endpoint(
    images: list[UploadFile] = File(...),
    provider_id: int = Depends(check_provider_role)
):
    """
    Upload images and get their URLs.
    """
    return await upload_service_images(images)

@router.post("/", response_model=ServiceCreationPaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_service_endpoint(
    data: ServiceCreate,
    provider_id: int = Depends(check_provider_role)
):
    """
    Create a new service with upfront platform and optional priority charges.
    Returns service metadata along with Stripe payment client_secret.
    """
    return await create_service(provider_id, data)

@router.post("/{service_id}/confirm-payment", response_model=ServiceResponse, status_code=status.HTTP_200_OK)
async def confirm_service_payment_endpoint(
    service_id: int = Path(..., title="The ID of the service to confirm payment for"),
    provider_id: int = Depends(check_provider_role)
):
    """
    Confirm Stripe payment for service creation and publish the service.
    """
    return await confirm_service_payment(provider_id, service_id)


@router.get("/my-services", response_model=ProviderServicesResponse, status_code=status.HTTP_200_OK)
async def get_my_services_endpoint(
    status: str = Query("ALL", description="Filter by status (ALL, DRAFT, PUBLISHED, PAUSED, CLOSED.)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    provider_id: int = Depends(check_provider_role)
):
    return await get_provider_services(provider_id, status, page, page_size)

@router.get("/", response_model=PaginatedServiceResponse, status_code=status.HTTP_200_OK)
async def get_all_services_endpoint(
    category: str = Query("ALL", description="Filter by category name"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100)
):
    return await get_all_services(category, page, page_size)

@router.get("/search", response_model=PaginatedServiceResponse, status_code=status.HTTP_200_OK)
async def search_services_endpoint(
    query: Optional[str] = Query(None, description="Search query string (matches any word in title or description)"),
    category: Optional[str] = Query(None, description="Optional category name to filter services"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100)
):
    """
    Public search endpoint to search published services matching keywords in title or description,
    optionally filtered by Category Name, with pagination.
    """
    return await search_services(query, category, page, page_size)

@router.get("/categories", response_model=ServiceCategoryListResponse, status_code=status.HTTP_200_OK)
async def get_service_categories_endpoint():
    """
    Get all unique categories from published services.
    """
    return await get_published_service_categories()

@router.get("/{service_id}", response_model=ServiceResponse, status_code=status.HTTP_200_OK)
async def get_service_by_id_endpoint(
    service_id: int = Path(..., title="The ID of the service to get")
):
    return await get_service_by_id(service_id)

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
