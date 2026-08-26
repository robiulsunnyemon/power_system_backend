from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.modules.admin import service, schemas
from app.modules.users.schemas import UserProfileResponse
from app.modules.messages.schemas import PaginatedMessageResponse
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

@router.get("/users", response_model=schemas.PaginatedUserResponse)
async def list_users(
    role: schemas.UserRoleFilter = schemas.UserRoleFilter.ALL,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    admin=Depends(get_current_admin)
):
    """
    Endpoint to list all users with role filtering and pagination.
    """
    return await service.get_all_users(role, page, page_size)

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

@router.get("/chat-history/{user1_id}/{user2_id}", response_model=PaginatedMessageResponse)
async def get_user_chat_history(
    user1_id: int,
    user2_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin=Depends(get_current_admin)
):
    """
    Endpoint for admin to get chat history between any two users with pagination.
    """
    return await service.get_user_chat_history(user1_id, user2_id, page, page_size)


# =========================================================================
# 1. Admin Payment Monitoring & Financial Analytics
# =========================================================================

@router.get("/payments/overview", response_model=schemas.PaymentOverviewResponse)
async def get_payment_overview(
    period: str = Query("monthly", pattern="^(weekly|monthly)$"),
    admin=Depends(get_current_admin)
):
    """
    Admin: Get comprehensive platform payment metrics, revenue streams, and timeline.
    """
    return await service.get_payment_overview(period)


# =========================================================================
# 2. Admin Transaction Management
# =========================================================================

@router.get("/transactions", response_model=schemas.PaginatedTransactionResponse)
async def list_transactions(
    type: schemas.TransactionType = None,
    status: schemas.TransactionStatus = None,
    search: str = Query(None, description="Search by user name, email, or Stripe charge ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    admin=Depends(get_current_admin)
):
    """
    Admin: View and filter all transactions across products and services with pagination.
    """
    return await service.get_all_transactions(
        type_filter=type,
        status_filter=status,
        search=search,
        page=page,
        page_size=page_size
    )

@router.get("/transactions/{transaction_id}", response_model=schemas.TransactionItem)
async def get_transaction(
    transaction_id: int,
    admin=Depends(get_current_admin)
):
    """
    Admin: Get single transaction details by ID.
    """
    return await service.get_transaction_by_id(transaction_id)


# =========================================================================
# 3. Admin Refund Management
# =========================================================================

@router.get("/refunds", response_model=schemas.PaginatedRefundResponse)
async def list_refunds(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    admin=Depends(get_current_admin)
):
    """
    Admin: List all refund transactions across the platform.
    """
    return await service.get_all_refunds(page, page_size)

@router.post("/refunds/process")
async def process_refund_endpoint(
    data: schemas.AdminProcessRefundRequest,
    admin=Depends(get_current_admin)
):
    """
    Admin: Execute an authoritative refund for an order or service application.
    """
    return await service.admin_process_refund(
        order_id=data.order_id,
        service_application_id=data.service_application_id,
        amount=data.amount,
        reason=data.reason,
        admin_id=admin.id
    )


# =========================================================================
# 4. Admin Escrow Release Controls
# =========================================================================

@router.get("/escrow/list", response_model=schemas.PaginatedEscrowListResponse)
async def list_escrow_holds(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    admin=Depends(get_current_admin)
):
    """
    Admin: List all active escrow holds for orders and services.
    """
    return await service.get_escrow_hold_list(page, page_size)

@router.post("/escrow/order/{order_id}/force-release")
async def force_release_order_escrow(
    order_id: int,
    admin=Depends(get_current_admin)
):
    """
    Admin: Force release escrow payment of an order directly to the seller.
    """
    return await service.admin_force_release_order_escrow(order_id, admin_id=admin.id)

@router.post("/escrow/order/{order_id}/force-refund")
async def force_refund_order_escrow(
    order_id: int,
    data: schemas.AdminEscrowActionRequest = schemas.AdminEscrowActionRequest(),
    admin=Depends(get_current_admin)
):
    """
    Admin: Force cancel escrow and refund the buyer for an order.
    """
    return await service.admin_force_refund_order_escrow(order_id, reason=data.reason, admin_id=admin.id)

@router.post("/escrow/service/{service_application_id}/force-release")
async def force_release_service_escrow(
    service_application_id: int,
    admin=Depends(get_current_admin)
):
    """
    Admin: Force release escrow payment of a service application to the service provider.
    """
    return await service.admin_force_release_service_escrow(service_application_id, admin_id=admin.id)

@router.post("/escrow/service/{service_application_id}/force-refund")
async def force_refund_service_escrow(
    service_application_id: int,
    data: schemas.AdminEscrowActionRequest = schemas.AdminEscrowActionRequest(),
    admin=Depends(get_current_admin)
):
    """
    Admin: Force cancel escrow and refund the client for a service application.
    """
    return await service.admin_force_refund_service_escrow(service_application_id, reason=data.reason, admin_id=admin.id)

