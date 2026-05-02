from app.core.db import db
from fastapi import HTTPException
from typing import List
from app.modules.orders.schemas import OrderCreate, OrderStatusUpdate
from app.modules.products.service import format_product_response
from prisma.enums import OrderStatus

def format_order_response(order):
    """
    Helper to format order data, including nested product and user details.
    """
    order_dict = order.model_dump()
    
    # Format Product if included
    if order.product:
        order_dict["product"] = format_product_response(order.product)
        
    # Format User if included (flattening profile image)
    if order.user:
        order_dict["user"] = {
            "id": order.user.id,
            "fullname": order.user.fullname,
            "email": order.user.email,
            "profile_image": order.user.profile.profile_image if order.user.profile else None
        }
        
    return order_dict

async def place_order(user_id: int, data: OrderCreate):
    """
    Places a new order and adds initial tracking: ORDERPLACE, ORDER PENDING.
    """
    # 1. Check if product exists and is active
    product = await db.product.find_unique(where={"id": data.product_id})
    if not product or product.status != "ACTIVE":
        raise HTTPException(status_code=404, detail="Product not available for order")
    
    # 2. Create order
    order = await db.order.create(
        data={
            "userId": user_id,
            "productId": data.product_id,
            "status": OrderStatus.PENDING,
            "tracking": {
                "create": [
                    {"status": "ORDERPLACE"},
                    {"status": "ORDER PENDING"}
                ]
            }
        },
        include={
            "product": {"include": {"category": True, "seller": {"include": {"profile": True}}}},
            "tracking": True
        }
    )
    
    return format_order_response(order)

async def get_buyer_orders(user_id: int):
    """
    Returns all orders placed by a specific buyer with tracking.
    """
    orders = await db.order.find_many(
        where={"userId": user_id},
        include={
            "product": {"include": {"category": True, "seller": {"include": {"profile": True}}}},
            "tracking": True
        },
        order={"createdAt": "desc"}
    )
    return [format_order_response(o) for o in orders]

async def get_seller_all_orders(seller_id: int):
    """
    Returns all orders for all products belonging to a specific seller with tracking.
    """
    orders = await db.order.find_many(
        where={
            "product": {
                "sellerId": seller_id
            }
        },
        include={
            "product": {"include": {"category": True, "seller": {"include": {"profile": True}}}},
            "user": {"include": {"profile": True}},
            "tracking": True
        },
        order={"createdAt": "desc"}
    )
    return [format_order_response(o) for o in orders]

async def get_orders_by_product(seller_id: int, product_id: int, status_filter: str = "ALL"):
    """
    Returns all orders for a specific product with status counts, optional filtering and tracking.
    """
    # 1. Verify product ownership
    product = await db.product.find_unique(where={"id": product_id})
    if not product or product.sellerId != seller_id:
        raise HTTPException(status_code=404, detail="Product not found or access denied")
        
    # 2. Fetch all orders for this product to calculate stats
    all_orders = await db.order.find_many(
        where={"productId": product_id},
        include={
            "product": {"include": {"category": True, "seller": {"include": {"profile": True}}}},
            "user": {"include": {"profile": True}},
            "tracking": True
        },
        order={"createdAt": "desc"}
    )
    
    # 3. Calculate stats
    total_accept = sum(1 for o in all_orders if o.status == OrderStatus.ACCEPTED)
    total_pending = sum(1 for o in all_orders if o.status == OrderStatus.PENDING)
    
    # 4. Apply filter
    if status_filter != "ALL":
        filtered_orders = [o for o in all_orders if o.status == status_filter]
    else:
        filtered_orders = all_orders
        
    return {
        "total_order": len(all_orders),
        "total_accept_order": total_accept,
        "total_pending_order": total_pending,
        "orders": [format_order_response(o) for o in filtered_orders]
    }

async def update_order_status(seller_id: int, order_id: int, data: OrderStatusUpdate):
    """
    Updates order status and adds tracking: 
    - ACCEPTED -> ORDER CONFIRM
    - DELIVERED -> ORDER DELIVERY
    """
    # 1. Fetch order with product details
    order = await db.order.find_unique(
        where={"id": order_id},
        include={"product": True}
    )
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    # 2. Verify ownership
    if order.product.sellerId != seller_id:
        raise HTTPException(status_code=403, detail="Access denied: You don't own this product")
        
    # 3. Determine tracking status
    tracking_data = []
    if data.status == OrderStatus.ACCEPTED:
        tracking_data.append({"status": "ORDER CONFIRM"})
    elif data.status == OrderStatus.DELIVERED:
        tracking_data.append({"status": "ORDER DELIVERY"})

    # 4. Update status and add tracking
    updated_order = await db.order.update(
        where={"id": order_id},
        data={
            "status": data.status,
            "tracking": {
                "create": tracking_data
            }
        },
        include={
            "product": {"include": {"category": True, "seller": {"include": {"profile": True}}}},
            "user": {"include": {"profile": True}},
            "tracking": True
        }
    )
    
    return format_order_response(updated_order)
