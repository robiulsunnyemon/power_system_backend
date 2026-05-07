from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List
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

@router.post("/", response_model=schemas.OrderResponse, tags=["Orders - Buyer"])
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
    status: schemas.OrderStatusFilter = Query(schemas.OrderStatusFilter.ALL),
    user_id: int = Depends(get_current_user_id)
):
    """
    Endpoint for buyers to see their own orders.
    """
    return await service.get_buyer_orders(user_id, status)


# --- SELLERS ENDPOINTS ---

@router.get("/seller/all", response_model=List[schemas.OrderResponse], tags=["Orders - Seller"])
async def list_all_seller_orders(
    status: schemas.OrderStatusFilter = Query(schemas.OrderStatusFilter.ALL),
    seller_id: int = Depends(check_seller_role)
):
    """
    Endpoint for sellers to see all orders for all of their products.
    """
    return await service.get_seller_all_orders(seller_id, status)

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
