from fastapi import APIRouter, Depends, Query, status
from typing import Optional
from prisma.enums import DisputeStatus, DisputeType
from app.modules.users.router import get_current_user_id
from app.modules.admin.router import get_current_admin
from app.modules.disputes import service, schemas

router = APIRouter(tags=["Disputes"])

# --- User Endpoints ---

@router.post("/disputes/order/{order_id}", response_model=schemas.DisputeResponse, status_code=status.HTTP_201_CREATED)
async def open_order_dispute(
    order_id: int,
    data: schemas.CreateDisputeRequest,
    current_user_id: int = Depends(get_current_user_id)
):
    """
    Buyer or Seller raises a dispute on a specific Order.
    """
    return await service.create_order_dispute(current_user_id, order_id, data)

@router.post("/disputes/service/{service_application_id}", response_model=schemas.DisputeResponse, status_code=status.HTTP_201_CREATED)
async def open_service_dispute(
    service_application_id: int,
    data: schemas.CreateDisputeRequest,
    current_user_id: int = Depends(get_current_user_id)
):
    """
    Client or Provider raises a dispute on a specific Service Application.
    """
    return await service.create_service_dispute(current_user_id, service_application_id, data)

@router.get("/disputes/my", response_model=schemas.PaginatedDisputeResponse)
async def get_my_disputes(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    Retrieve disputes raised by or against the current authenticated user.
    """
    return await service.get_user_disputes(current_user_id, page, page_size)


# --- Admin Endpoints ---

@router.get("/admin/disputes", response_model=schemas.PaginatedDisputeResponse)
async def list_admin_disputes(
    status: Optional[DisputeStatus] = None,
    dispute_type: Optional[DisputeType] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    admin=Depends(get_current_admin)
):
    """
    Admin: List and filter all platform disputes with pagination.
    """
    return await service.get_admin_disputes(status, dispute_type, page, page_size)

@router.get("/admin/disputes/{dispute_id}", response_model=schemas.DisputeResponse)
async def get_admin_dispute_detail(
    dispute_id: int,
    admin=Depends(get_current_admin)
):
    """
    Admin: Retrieve full dispute details with order/service and participant data.
    """
    return await service.get_dispute_by_id(dispute_id)

@router.patch("/admin/disputes/{dispute_id}/resolve", response_model=schemas.DisputeResponse)
async def resolve_dispute_endpoint(
    dispute_id: int,
    data: schemas.ResolveDisputeRequest,
    admin=Depends(get_current_admin)
):
    """
    Admin: Resolve a dispute (with automated buyer refund or seller escrow release).
    """
    return await service.resolve_dispute(dispute_id, data, admin_id=admin.id)
