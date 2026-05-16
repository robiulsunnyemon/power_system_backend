from app.core.db import db
from fastapi import HTTPException
from typing import List,Optional
from app.modules.orders import schemas
from app.modules.products.service import format_product_response
from prisma.enums import OrderStatus, ProductStatus
from app.modules.notifications.service import send_notification
from app.common.utils import calculate_trust_score
from datetime import datetime, timedelta, timezone

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

async def place_order(user_id: int, data: schemas.OrderCreate):
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
    
    # Notify Seller
    seller_id = order.product.sellerId
    await send_notification(
        user_id=seller_id,
        title="New Order Received",
        description=f"You have received a new order for '{order.product.title}'.",
        notification_type="order",
        image=order.product.images[0] if order.product.images else None
    )
    
    return format_order_response(order)

async def get_buyer_orders(user_id: int, status_filter: str = "ALL", order_id: Optional[int] = None):
    """
    Returns all orders placed by a specific buyer with tracking, optionally filtered by status and order ID.
    """
    where = {"userId": user_id}
    if status_filter != "ALL":
        where["status"] = status_filter
    
    if order_id:
        where["id"] = order_id

    orders = await db.order.find_many(
        where=where,
        include={
            "product": {"include": {"category": True, "seller": {"include": {"profile": True}}}},
            "tracking": True
        },
        order={"createdAt": "desc"}
    )
    return [format_order_response(o) for o in orders]

async def get_seller_all_orders(seller_id: int, status_filter: str = "ALL", page: int = 1, page_size: int = 10):
    """
    Returns all orders for all products belonging to a specific seller with tracking, optionally filtered by status and paginated.
    """
    where = {
        "product": {
            "sellerId": seller_id
        }
    }
    if status_filter != "ALL":
        where["status"] = status_filter

    total = await db.order.count(where=where)

    orders = await db.order.find_many(
        where=where,
        include={
            "product": {"include": {"category": True, "seller": {"include": {"profile": True}}}},
            "user": {"include": {"profile": True}},
            "tracking": True
        },
        order={"createdAt": "desc"},
        skip=(page - 1) * page_size,
        take=page_size
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "orders": [format_order_response(o) for o in orders]
    }

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

async def update_order_status(seller_id: int, order_id: int, data: schemas.OrderStatusUpdate):
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

    # 5. Update Seller Trust Score on Delivery
    if data.status == OrderStatus.DELIVERED:
        # Fetch current profile or assume 0 if not exists
        profile = await db.userprofile.find_unique(where={"userId": order.product.sellerId})
        current_raw = profile.raw_score if profile else 0
        
        new_raw = current_raw + 200
        new_trust = calculate_trust_score(new_raw)
        
        # Use upsert to handle cases where profile doesn't exist
        await db.userprofile.upsert(
            where={"userId": order.product.sellerId},
            data={
                "create": {
                    "userId": order.product.sellerId,
                    "raw_score": new_raw,
                    "trust_score": new_trust
                },
                "update": {
                    "raw_score": new_raw,
                    "trust_score": new_trust
                }
            }
        )
    
    # Notify Buyer
    status_msg_map = {
        OrderStatus.ACCEPTED: "Your order has been accepted.",
        OrderStatus.DELIVERED: "Your order has been delivered successfully.",
        OrderStatus.CANCELLED: "Your order has been cancelled."
    }
    
    if data.status in status_msg_map:
        await send_notification(
            user_id=updated_order.userId,
            title=f"Order Update: {data.status}",
            description=status_msg_map[data.status],
            notification_type="order",
            image=updated_order.product.images[0] if updated_order.product.images else None
        )
    
    return format_order_response(updated_order)

async def get_seller_dashboard_stats(seller_id: int):
    """
    Calculates seller performance metrics including lifetime total revenue, 
    active products, pending orders, and revenue growth compared to last month.
    """
    now = datetime.now(timezone.utc)
    
    # --- 1. Total Revenue (Lifetime) ---
    delivered_orders = await db.order.find_many(
        where={
            "product": {"sellerId": seller_id},
            "status": OrderStatus.DELIVERED
        },
        include={"product": True}
    )
    total_revenue = sum(o.product.total_fee for o in delivered_orders)

    # --- 2. Operational Counts ---
    total_active_products = await db.product.count(
        where={
            "sellerId": seller_id,
            "status": ProductStatus.ACTIVE
        }
    )

    total_pending_orders = await db.order.count(
        where={
            "product": {"sellerId": seller_id},
            "status": OrderStatus.PENDING
        }
    )

    # --- 3. Revenue Growth (Current Month vs Last Month) ---
    first_day_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    if first_day_this_month.month == 1:
        first_day_last_month = first_day_this_month.replace(year=first_day_this_month.year - 1, month=12)
    else:
        first_day_last_month = first_day_this_month.replace(month=first_day_this_month.month - 1)
    
    last_day_last_month = first_day_this_month - timedelta(seconds=1)

    # Revenue this month
    this_month_orders = [o for o in delivered_orders if o.createdAt >= first_day_this_month]
    revenue_this_month = sum(o.product.total_fee for o in this_month_orders)

    # Revenue last month
    last_month_orders = [o for o in delivered_orders if first_day_last_month <= o.createdAt <= last_day_last_month]
    revenue_last_month = sum(o.product.total_fee for o in last_month_orders)

    # Calculate growth %
    if revenue_last_month == 0:
        growth_pct = 100.0 if revenue_this_month > 0 else 0.0
    else:
        growth_pct = round(((revenue_this_month - revenue_last_month) / revenue_last_month) * 100, 2)

    return {
        "total_revenue": total_revenue,
        "total_active_products": total_active_products,
        "total_pending_orders": total_pending_orders,
        "revenue_growth_pct": growth_pct
    }

async def get_seller_revenue_growth(seller_id: int, filter_type: schemas.GrowthFilter):
    """
    Returns revenue data points for charting based on the selected filter.
    """
    now = datetime.now(timezone.utc)
    data_points = []

    if filter_type == schemas.GrowthFilter.WEEKLY:
        for i in range(6, -1, -1):
            day = now - timedelta(days=i)
            start_date = day.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = day.replace(hour=23, minute=59, second=59, microsecond=999999)
            orders = await db.order.find_many(
                where={
                    "product": {"sellerId": seller_id},
                    "status": OrderStatus.DELIVERED,
                    "createdAt": {"gte": start_date, "lte": end_date}
                },
                include={"product": True}
            )
            revenue = sum(o.product.total_fee for o in orders)
            data_points.append({"label": day.strftime("%a"), "revenue": revenue})

    elif filter_type == schemas.GrowthFilter.MONTHLY:
        for i in range(29, -1, -1):
            day = now - timedelta(days=i)
            start_date = day.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = day.replace(hour=23, minute=59, second=59, microsecond=999999)
            orders = await db.order.find_many(
                where={
                    "product": {"sellerId": seller_id},
                    "status": OrderStatus.DELIVERED,
                    "createdAt": {"gte": start_date, "lte": end_date}
                },
                include={"product": True}
            )
            revenue = sum(o.product.total_fee for o in orders)
            data_points.append({"label": day.strftime("%d %b"), "revenue": revenue})

    elif filter_type in [schemas.GrowthFilter.SIX_MONTHS, schemas.GrowthFilter.YEARLY]:
        months_to_show = 6 if filter_type == schemas.GrowthFilter.SIX_MONTHS else 12
        for i in range(months_to_show - 1, -1, -1):
            target_month = now.month - i
            target_year = now.year
            while target_month <= 0:
                target_month += 12
                target_year -= 1
            
            month_start = datetime(target_year, target_month, 1)
            if target_month == 12:
                next_month_start = datetime(target_year + 1, 1, 1)
            else:
                next_month_start = datetime(target_year, target_month + 1, 1)
                
            orders = await db.order.find_many(
                where={
                    "product": {"sellerId": seller_id},
                    "status": OrderStatus.DELIVERED,
                    "createdAt": {"gte": month_start, "lt": next_month_start}
                },
                include={"product": True}
            )
            revenue = sum(o.product.total_fee for o in orders)
            data_points.append({"label": month_start.strftime("%b %y"), "revenue": revenue})

    elif filter_type == schemas.GrowthFilter.YEAR_RANGE:
        for i in range(4, -1, -1):
            year_start = datetime(now.year - i, 1, 1)
            year_end = datetime(now.year - i + 1, 1, 1)
            orders = await db.order.find_many(
                where={
                    "product": {"sellerId": seller_id},
                    "status": OrderStatus.DELIVERED,
                    "createdAt": {"gte": year_start, "lt": year_end}
                },
                include={"product": True}
            )
            revenue = sum(o.product.total_fee for o in orders)
            data_points.append({"label": str(year_start.year), "revenue": revenue})

    return {"data": data_points}
