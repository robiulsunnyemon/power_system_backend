from fastapi import APIRouter, Depends, HTTPException, Query,status
from typing import List, Optional
from app.modules.orders import service, schemas
from app.modules.users.router import get_current_user_id
from app.core.db import db

router = APIRouter(prefix="/orders")

# Dependency to check if user is a SELLER
async def check_seller_role(user_id: int = Depends(get_current_user_id)):
    user = await db.user.find_unique(where={"id": user_id})
    if not user or "SELLER" not in user.roles:
        raise HTTPException(
            status_code=403, 
            detail="Only sellers can perform this action"
        )
    return user_id

# --- BUYERS ENDPOINTS ---

@router.post("/", response_model=schemas.OrderResponse, tags=["Orders - Buyer"],status_code=status.HTTP_201_CREATED)
async def create_order(
    data: schemas.OrderCreate,
    user_id: int = Depends(get_current_user_id)
):
    """
    Endpoint for buyers to place a new order.
    """
    return await service.place_order(user_id, data)

@router.get("/my", response_model=List[schemas.OrderResponse], tags=["Orders - Buyer"])
async def list_my_orders(
    order_id: Optional[int] = Query(None, description="Optional: Filter by a specific order ID"),
    status: schemas.OrderStatusFilter = Query(schemas.OrderStatusFilter.ALL),
    user_id: int = Depends(get_current_user_id)
):
    """
    Endpoint for buyers to see their own orders.
    """
    return await service.get_buyer_orders(user_id, status, order_id)


# --- SELLERS ENDPOINTS ---

@router.get("/seller/all", response_model=schemas.PaginatedOrderResponse, tags=["Orders - Seller"])
async def list_all_seller_orders(
    status: schemas.OrderStatusFilter = Query(schemas.OrderStatusFilter.ALL),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    seller_id: int = Depends(check_seller_role)
):
    """
    Endpoint for sellers to see all orders for all of their products with pagination.
    """
    return await service.get_seller_all_orders(seller_id, status, page, page_size)

@router.get("/seller/product/{product_id}", response_model=schemas.ProductOrdersResponse, tags=["Orders - Seller"])
async def list_orders_by_product(
    product_id: int,
    status: schemas.OrderStatusFilter = schemas.OrderStatusFilter.ALL,
    seller_id: int = Depends(check_seller_role)
):
    """
    Endpoint for sellers to see all orders for a specific product with filtering and counts.
    """
    return await service.get_orders_by_product(seller_id, product_id, status)

@router.patch("/{order_id}/status", response_model=schemas.OrderResponse, tags=["Orders - Seller"])
async def update_status(
    order_id: int,
    data: schemas.OrderStatusUpdate,
    seller_id: int = Depends(check_seller_role)
):
    """
    Endpoint for sellers to accept or cancel an order.
    """
    return await service.update_order_status(seller_id, order_id, data)

@router.get("/seller/dashboard/stats", response_model=schemas.SellerDashboardStats, tags=["Orders - Seller"])
async def get_seller_stats(
    seller_id: int = Depends(check_seller_role)
):
    """
    Endpoint for sellers to see their lifetime dashboard statistics.
    """
    return await service.get_seller_dashboard_stats(seller_id)

@router.get("/seller/dashboard/revenue-growth", response_model=schemas.RevenueGrowthResponse, tags=["Orders - Seller"])
async def get_seller_revenue_growth(
    filter: schemas.GrowthFilter = Query(schemas.GrowthFilter.WEEKLY),
    seller_id: int = Depends(check_seller_role)
):
    """
    Endpoint for sellers to see their revenue growth data points for charts.
    """
    return await service.get_seller_revenue_growth(seller_id, filter)
