from app.core.db import db
from prisma.enums import (
    Role,
    AccountStatus,
    PaymentStatus,
    PaymentMethod,
    OrderStatus,
    ProductStatus,
    TransactionType,
    TransactionStatus
)
from app.modules.admin.schemas import UserRoleFilter, GrowthFilter
from fastapi import HTTPException
from app.core.websocket import manager
from datetime import datetime, timedelta, timezone

async def get_all_users(role_filter: UserRoleFilter, page: int = 1, page_size: int = 10):
    """
    Fetches all users with their profile data, optionally filtered by role, with pagination.
    """
    query = {}
    if role_filter != UserRoleFilter.ALL:
        # Map the filter enum to the Prisma Role enum
        query["roles"] = {"has": Role(role_filter.value)}
    
    total = await db.user.count(where=query)
    
    users = await db.user.find_many(
        where=query,
        include={"profile": True},
        skip=(page - 1) * page_size,
        take=page_size,
        order={"createdAt": "desc"}
    )
    
    # Flatten the profile_image into the response format
    result = []
    for user in users:
        user_dict = user.model_dump()
        user_dict["profile_image"] = user.profile.profile_image if user.profile else None
        user_dict["trust_score"] = user.profile.trust_score if user.profile else 0
        user_dict["raw_score"] = user.profile.raw_score if user.profile else 0
        user_dict["is_online"] = manager.is_user_online(user.id)
        user_dict["is_stripe_active"] = bool(user.payoutsEnabled and user.chargesEnabled)
        result.append(user_dict)
    
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "users": result
    }

async def update_user_status(user_id: int, status):
    """
    Updates the accountStatus of a specific user.
    """
    user = await db.user.find_unique(where={"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    updated_user = await db.user.update(
        where={"id": user_id},
        data={"accountStatus": status},
        include={"profile": True}
    )
    
    user_dict = updated_user.model_dump()
    user_dict["profile_image"] = updated_user.profile.profile_image if updated_user.profile else None
    user_dict["trust_score"] = updated_user.profile.trust_score if updated_user.profile else 0
    user_dict["raw_score"] = updated_user.profile.raw_score if updated_user.profile else 0
    user_dict["is_online"] = manager.is_user_online(user.id)
    user_dict["is_stripe_active"] = bool(updated_user.payoutsEnabled and updated_user.chargesEnabled)
    return user_dict

def calculate_growth_pct(current: int, previous: int) -> float:
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - previous) / previous) * 100, 2)

async def get_dashboard_stats():
    now = datetime.now(timezone.utc)
    first_day_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Last month range
    if first_day_this_month.month == 1:
        first_day_last_month = first_day_this_month.replace(year=first_day_this_month.year - 1, month=12)
    else:
        first_day_last_month = first_day_this_month.replace(month=first_day_this_month.month - 1)
    
    last_day_last_month = first_day_this_month - timedelta(seconds=1)

    # Current Stats
    total_users = await db.user.count()
    active_users = await db.user.count(where={"accountStatus": AccountStatus.ACTIVE})
    pending_users = await db.user.count(where={"accountStatus": AccountStatus.PENDING})

    # Growth Stats (New users created in the month)
    new_this_month = await db.user.count(where={"createdAt": {"gte": first_day_this_month}})
    new_last_month = await db.user.count(where={"createdAt": {"gte": first_day_last_month, "lte": last_day_last_month}})
    
    active_new_this_month = await db.user.count(where={"accountStatus": AccountStatus.ACTIVE, "createdAt": {"gte": first_day_this_month}})
    active_new_last_month = await db.user.count(where={"accountStatus": AccountStatus.ACTIVE, "createdAt": {"gte": first_day_last_month, "lte": last_day_last_month}})

    pending_new_this_month = await db.user.count(where={"accountStatus": AccountStatus.PENDING, "createdAt": {"gte": first_day_this_month}})
    pending_new_last_month = await db.user.count(where={"accountStatus": AccountStatus.PENDING, "createdAt": {"gte": first_day_last_month, "lte": last_day_last_month}})

    # Financial Stats (Product Orders + Service Applications)
    paid_orders = await db.order.find_many(where={"paymentStatus": "PAID"})
    paid_services = await db.serviceapplication.find_many(where={"paymentStatus": "PAID"})
    
    total_platform_revenue = sum(o.platformFee + o.protectionFee + o.escrowFee for o in paid_orders) + sum(s.platformFee + s.protectionFee + s.escrowFee for s in paid_services)
    total_transaction_volume = sum(o.totalAmount for o in paid_orders) + sum(s.totalAmount for s in paid_services)
    active_stripe_users = await db.user.count(where={"payoutsEnabled": True, "chargesEnabled": True})

    return {
        "total_users": total_users,
        "active_users": active_users,
        "pending_users": pending_users,
        "total_growth_pct": calculate_growth_pct(new_this_month, new_last_month),
        "active_growth_pct": calculate_growth_pct(active_new_this_month, active_new_last_month),
        "pending_growth_pct": calculate_growth_pct(pending_new_this_month, pending_new_last_month),
        "total_platform_revenue": total_platform_revenue,
        "total_transaction_volume": total_transaction_volume,
        "active_stripe_users": active_stripe_users
    }

async def get_user_growth(filter_type: GrowthFilter):
    now = datetime.now(timezone.utc)
    data_points = []

    if filter_type == GrowthFilter.WEEKLY:
        for i in range(6, -1, -1):
            day = now - timedelta(days=i)
            start_date = day.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = day.replace(hour=23, minute=59, second=59, microsecond=999999)
            count = await db.user.count(where={"createdAt": {"gte": start_date, "lte": end_date}})
            data_points.append({"label": day.strftime("%a"), "count": count})

    elif filter_type == GrowthFilter.MONTHLY:
        for i in range(29, -1, -1):
            day = now - timedelta(days=i)
            start_date = day.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = day.replace(hour=23, minute=59, second=59, microsecond=999999)
            count = await db.user.count(where={"createdAt": {"gte": start_date, "lte": end_date}})
            data_points.append({"label": day.strftime("%d %b"), "count": count})

    elif filter_type in [GrowthFilter.SIX_MONTHS, GrowthFilter.YEARLY]:
        months_to_show = 6 if filter_type == GrowthFilter.SIX_MONTHS else 12
        for i in range(months_to_show - 1, -1, -1):
            # Calculate month start
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
                
            count = await db.user.count(where={"createdAt": {"gte": month_start, "lt": next_month_start}})
            data_points.append({"label": month_start.strftime("%b %y"), "count": count})

    elif filter_type == GrowthFilter.YEAR_RANGE:
        for i in range(4, -1, -1):
            year_start = datetime(now.year - i, 1, 1)
            year_end = datetime(now.year - i + 1, 1, 1)
            count = await db.user.count(where={"createdAt": {"gte": year_start, "lt": year_end}})
            data_points.append({"label": str(year_start.year), "count": count})

    return {"data": data_points}

async def get_user_chat_history(user1_id: int, user2_id: int, page: int = 1, page_size: int = 20):
    """
    Fetches the full chat history between any two users (Admin only) with pagination.
    """
    from app.modules.messages.service import get_chat_history
    return await get_chat_history(user1_id, user2_id, page, page_size)


# =========================================================================
# 1. Admin Payment Monitoring & Financial Analytics
# =========================================================================

async def get_payment_overview(period: str = "monthly"):
    """
    Returns platform financial breakdown, revenue streams, payment methods, and historical trend.
    """
    now = datetime.now(timezone.utc)

    # 1. Paid Orders & Paid Service Apps
    paid_orders = await db.order.find_many(where={"paymentStatus": PaymentStatus.PAID})
    paid_services = await db.serviceapplication.find_many(where={"paymentStatus": PaymentStatus.PAID})
    
    # Priority boost service fees
    boosted_services = await db.service.find_many(where={"priorityFeePaid": {"gt": 0}})
    priority_boost_revenue = sum(s.priorityFeePaid for s in boosted_services)

    # Revenues
    product_revenue = sum(o.platformFee + o.protectionFee + o.escrowFee for o in paid_orders)
    product_volume = sum(o.totalAmount for o in paid_orders)
    
    service_revenue = sum(s.platformFee + s.protectionFee + s.escrowFee for s in paid_services)
    service_volume = sum(s.totalAmount for s in paid_services)
    
    total_platform_revenue = product_revenue + service_revenue + priority_boost_revenue
    total_transaction_volume = product_volume + service_volume

    # 2. Escrow Held
    held_orders = await db.order.find_many(where={"paymentStatus": PaymentStatus.HELD_IN_ESCROW})
    held_services = await db.serviceapplication.find_many(where={"paymentStatus": PaymentStatus.HELD_IN_ESCROW})
    total_escrow_held_volume = sum(o.totalAmount for o in held_orders) + sum(s.totalAmount for s in held_services)

    # 3. Refunds Volume
    refund_transactions = await db.transaction.find_many(where={"type": "REFUND", "status": "COMPLETED"})
    total_refund_volume = sum(t.amount for t in refund_transactions)

    # 4. Active Connected Stripe Sellers
    active_stripe_sellers = await db.user.count(where={"payoutsEnabled": True, "chargesEnabled": True})

    # 5. Payment Method Distribution
    all_orders = await db.order.find_many()
    all_services = await db.serviceapplication.find_many()
    
    stripe_orders = [o for o in all_orders if o.paymentMethod == "STRIPE"]
    stripe_services = [s for s in all_services if s.paymentMethod == "STRIPE"]
    cod_orders = [o for o in all_orders if o.paymentMethod == "COD"]
    cod_services = [s for s in all_services if s.paymentMethod == "COD"]

    payment_method_distribution = {
        "stripe_volume": sum(o.totalAmount for o in stripe_orders) + sum(s.totalAmount for s in stripe_services),
        "stripe_count": len(stripe_orders) + len(stripe_services),
        "cod_volume": sum(o.totalAmount for o in cod_orders) + sum(s.totalAmount for s in cod_services),
        "cod_count": len(cod_orders) + len(cod_services),
    }

    # 6. Revenue Trend Timeline
    days_back = 7 if period == "weekly" else 30
    trend_points = []
    for i in range(days_back - 1, -1, -1):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        day_orders = [o for o in paid_orders if day_start <= o.createdAt <= day_end]
        day_services = [s for s in paid_services if day_start <= s.createdAt <= day_end]
        
        day_rev = sum(o.platformFee + o.protectionFee + o.escrowFee for o in day_orders) + sum(s.platformFee + s.protectionFee + s.escrowFee for s in day_services)
        day_vol = sum(o.totalAmount for o in day_orders) + sum(s.totalAmount for s in day_services)
        
        trend_points.append({
            "date": day.strftime("%Y-%m-%d"),
            "revenue": round(day_rev, 2),
            "volume": round(day_vol, 2),
            "transaction_count": len(day_orders) + len(day_services)
        })

    return {
        "total_platform_revenue": round(total_platform_revenue, 2),
        "total_transaction_volume": round(total_transaction_volume, 2),
        "total_escrow_held_volume": round(total_escrow_held_volume, 2),
        "total_refund_volume": round(total_refund_volume, 2),
        "active_stripe_connect_sellers": active_stripe_sellers,
        "channel_breakdown": {
            "product_revenue": round(product_revenue, 2),
            "product_volume": round(product_volume, 2),
            "service_revenue": round(service_revenue, 2),
            "service_volume": round(service_volume, 2),
            "priority_boost_revenue": round(priority_boost_revenue, 2)
        },
        "payment_method_distribution": payment_method_distribution,
        "revenue_trend": trend_points
    }


# =========================================================================
# 2. Admin Transaction Management
# =========================================================================

async def get_all_transactions(
    type_filter=None,
    status_filter=None,
    search: str = None,
    start_date: datetime = None,
    end_date: datetime = None,
    page: int = 1,
    page_size: int = 10
):
    query = {}
    if type_filter:
        query["type"] = type_filter
    if status_filter:
        query["status"] = status_filter
        
    date_query = {}
    if start_date:
        date_query["gte"] = start_date
    if end_date:
        date_query["lte"] = end_date
    if date_query:
        query["createdAt"] = date_query

    if search:
        query["OR"] = [
            {"user": {"fullname": {"contains": search, "mode": "insensitive"}}},
            {"user": {"email": {"contains": search, "mode": "insensitive"}}},
            {"stripeChargeId": {"contains": search, "mode": "insensitive"}},
        ]

    total = await db.transaction.count(where=query)
    transactions = await db.transaction.find_many(
        where=query,
        include={
            "user": True,
            "order": {"include": {"product": True}},
            "serviceApplication": {"include": {"service": True}}
        },
        skip=(page - 1) * page_size,
        take=page_size,
        order={"createdAt": "desc"}
    )

    items = []
    for tx in transactions:
        user_info = {
            "id": tx.user.id if tx.user else 0,
            "fullname": tx.user.fullname if tx.user else "Unknown",
            "email": tx.user.email if tx.user else ""
        }
        
        order_details = None
        if tx.order:
            order_details = {
                "order_id": tx.order.id,
                "status": tx.order.status,
                "product_title": tx.order.product.title if tx.order.product else None,
                "subtotal": tx.order.subTotal,
                "total_amount": tx.order.totalAmount,
                "payment_method": tx.order.paymentMethod,
                "payment_status": tx.order.paymentStatus
            }
            
        service_details = None
        if tx.serviceApplication:
            service_details = {
                "service_application_id": tx.serviceApplication.id,
                "status": tx.serviceApplication.status,
                "service_title": tx.serviceApplication.service.title if tx.serviceApplication.service else None,
                "subtotal": tx.serviceApplication.subTotal,
                "total_amount": tx.serviceApplication.totalAmount,
                "payment_method": tx.serviceApplication.paymentMethod,
                "payment_status": tx.serviceApplication.paymentStatus
            }

        items.append({
            "id": tx.id,
            "amount": tx.amount,
            "currency": tx.currency,
            "type": tx.type,
            "status": tx.status,
            "stripeChargeId": tx.stripeChargeId,
            "createdAt": tx.createdAt,
            "updatedAt": tx.updatedAt,
            "user": user_info,
            "orderId": tx.orderId,
            "order_details": order_details,
            "serviceApplicationId": tx.serviceApplicationId,
            "service_details": service_details
        })

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "transactions": items
    }

async def get_transaction_by_id(transaction_id: int):
    tx = await db.transaction.find_unique(
        where={"id": transaction_id},
        include={
            "user": True,
            "order": {"include": {"product": True}},
            "serviceApplication": {"include": {"service": True}}
        }
    )
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    user_info = {
        "id": tx.user.id if tx.user else 0,
        "fullname": tx.user.fullname if tx.user else "Unknown",
        "email": tx.user.email if tx.user else ""
    }
    
    order_details = None
    if tx.order:
        order_details = {
            "order_id": tx.order.id,
            "status": tx.order.status,
            "product_title": tx.order.product.title if tx.order.product else None,
            "subtotal": tx.order.subTotal,
            "total_amount": tx.order.totalAmount,
            "payment_method": tx.order.paymentMethod,
            "payment_status": tx.order.paymentStatus
        }
        
    service_details = None
    if tx.serviceApplication:
        service_details = {
            "service_application_id": tx.serviceApplication.id,
            "status": tx.serviceApplication.status,
            "service_title": tx.serviceApplication.service.title if tx.serviceApplication.service else None,
            "subtotal": tx.serviceApplication.subTotal,
            "total_amount": tx.serviceApplication.totalAmount,
            "payment_method": tx.serviceApplication.paymentMethod,
            "payment_status": tx.serviceApplication.paymentStatus
        }

    return {
        "id": tx.id,
        "amount": tx.amount,
        "currency": tx.currency,
        "type": tx.type,
        "status": tx.status,
        "stripeChargeId": tx.stripeChargeId,
        "createdAt": tx.createdAt,
        "updatedAt": tx.updatedAt,
        "user": user_info,
        "orderId": tx.orderId,
        "order_details": order_details,
        "serviceApplicationId": tx.serviceApplicationId,
        "service_details": service_details
    }


# =========================================================================
# 3. Admin Refund Management
# =========================================================================

async def get_all_refunds(page: int = 1, page_size: int = 10):
    """
    Returns all refund transactions across orders and services.
    """
    total = await db.transaction.count(where={"type": "REFUND"})
    refunds = await db.transaction.find_many(
        where={"type": "REFUND"},
        include={
            "user": True,
            "order": {"include": {"product": True}},
            "serviceApplication": {"include": {"service": True}}
        },
        skip=(page - 1) * page_size,
        take=page_size,
        order={"createdAt": "desc"}
    )

    items = []
    for r in refunds:
        title = "Direct Platform Refund"
        if r.order and r.order.product:
            title = f"Order #{r.order.id} - {r.order.product.title}"
        elif r.serviceApplication and r.serviceApplication.service:
            title = f"Service App #{r.serviceApplication.id} - {r.serviceApplication.service.title}"

        items.append({
            "transaction_id": r.id,
            "amount": r.amount,
            "currency": r.currency,
            "createdAt": r.createdAt,
            "user": {
                "id": r.user.id if r.user else 0,
                "fullname": r.user.fullname if r.user else "Unknown",
                "email": r.user.email if r.user else ""
            },
            "order_id": r.orderId,
            "service_application_id": r.serviceApplicationId,
            "stripe_charge_id": r.stripeChargeId,
            "title": title
        })

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "refunds": items
    }

async def admin_process_refund(order_id: int = None, service_application_id: int = None, amount: float = None, reason: str = "", admin_id: int = None):
    """
    Admin authoritative refund execution with Stripe integration.
    """
    from app.modules.payments.service import refund_payment
    from prisma.enums import OrderStatus, ProductStatus

    if not order_id and not service_application_id:
        raise HTTPException(status_code=400, detail="Either order_id or service_application_id must be provided")

    if order_id:
        order = await db.order.find_unique(where={"id": order_id}, include={"product": True})
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if not order.stripeIntentId:
            raise HTTPException(status_code=400, detail="Order has no associated Stripe Payment Intent")

        refund_amount = amount if amount is not None else order.totalAmount
        try:
            refund_res = await refund_payment(order.stripeIntentId, refund_amount)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Stripe refund failed: {str(e)}")

        await db.order.update(
            where={"id": order.id},
            data={
                "paymentStatus": PaymentStatus.REFUNDED,
                "status": OrderStatus.CANCELLED,
                "tracking": {"create": [{"status": f"ADMIN REFUND ISSUED: {reason}"}]}
            }
        )
        if order.productId:
            await db.product.update(
                where={"id": order.productId},
                data={"status": ProductStatus.ACTIVE}
            )

        charge_id = str(getattr(refund_res, "id", ""))
        tx = await db.transaction.create(data={
            "amount": refund_amount,
            "currency": "USD",
            "type": "REFUND",
            "status": "COMPLETED",
            "stripeChargeId": charge_id,
            "userId": order.userId,
            "orderId": order.id
        })

        return {
            "status": "success",
            "message": f"Order #{order.id} refunded successfully by Admin",
            "transaction_id": tx.id,
            "refund_amount": refund_amount
        }

    elif service_application_id:
        service_app = await db.serviceapplication.find_unique(where={"id": service_application_id})
        if not service_app:
            raise HTTPException(status_code=404, detail="Service application not found")
        if not service_app.stripeIntentId:
            raise HTTPException(status_code=400, detail="Service application has no associated Stripe Payment Intent")

        refund_amount = amount if amount is not None else service_app.totalAmount
        try:
            refund_res = await refund_payment(service_app.stripeIntentId, refund_amount)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Stripe refund failed: {str(e)}")

        await db.serviceapplication.update(
            where={"id": service_app.id},
            data={
                "paymentStatus": PaymentStatus.REFUNDED,
                "status": "DECLINED"
            }
        )

        charge_id = str(getattr(refund_res, "id", ""))
        tx = await db.transaction.create(data={
            "amount": refund_amount,
            "currency": "USD",
            "type": "REFUND",
            "status": "COMPLETED",
            "stripeChargeId": charge_id,
            "userId": service_app.clientId,
            "serviceApplicationId": service_app.id
        })

        return {
            "status": "success",
            "message": f"Service application #{service_app.id} refunded successfully by Admin",
            "transaction_id": tx.id,
            "refund_amount": refund_amount
        }


# =========================================================================
# 4. Admin Escrow Release & Controls
# =========================================================================

async def get_escrow_hold_list(page: int = 1, page_size: int = 10):
    """
    Returns all active orders and services currently locked in Escrow.
    """
    now = datetime.now(timezone.utc)
    
    held_orders = await db.order.find_many(
        where={"paymentStatus": PaymentStatus.HELD_IN_ESCROW},
        include={"user": True, "product": {"include": {"seller": True}}},
        order={"createdAt": "desc"}
    )
    
    held_services = await db.serviceapplication.find_many(
        where={"paymentStatus": PaymentStatus.HELD_IN_ESCROW},
        include={"client": True, "service": {"include": {"provider": True}}},
        order={"createdAt": "desc"}
    )

    combined_items = []
    for o in held_orders:
        days_held = (now - o.createdAt).days if o.createdAt else 0
        buyer_summary = {
            "id": o.user.id if o.user else 0,
            "fullname": o.user.fullname if o.user else "Unknown Buyer",
            "email": o.user.email if o.user else ""
        }
        seller_summary = None
        if o.product and o.product.seller:
            seller_summary = {
                "id": o.product.seller.id,
                "fullname": o.product.seller.fullname,
                "email": o.product.seller.email
            }
        
        combined_items.append({
            "type": "ORDER",
            "id": o.id,
            "subtotal": o.subTotal,
            "platform_fee": o.platformFee,
            "protection_fee": o.protectionFee,
            "escrow_fee": o.escrowFee,
            "total_amount": o.totalAmount,
            "payment_status": str(o.paymentStatus),
            "stripe_intent_id": o.stripeIntentId,
            "days_held": max(0, days_held),
            "created_at": o.createdAt,
            "buyer_or_client": buyer_summary,
            "seller_or_provider": seller_summary,
            "item_title": o.product.title if o.product else f"Order #{o.id}"
        })

    for s in held_services:
        days_held = (now - s.createdAt).days if s.createdAt else 0
        client_summary = {
            "id": s.client.id if s.client else 0,
            "fullname": s.client.fullname if s.client else "Unknown Client",
            "email": s.client.email if s.client else ""
        }
        provider_summary = None
        if s.service and s.service.provider:
            provider_summary = {
                "id": s.service.provider.id,
                "fullname": s.service.provider.fullname,
                "email": s.service.provider.email
            }

        combined_items.append({
            "type": "SERVICE",
            "id": s.id,
            "subtotal": s.proposedRate if hasattr(s, "proposedRate") else s.subTotal,
            "platform_fee": s.platformFee,
            "protection_fee": s.protectionFee,
            "escrow_fee": s.escrowFee,
            "total_amount": s.totalAmount,
            "payment_status": str(s.paymentStatus),
            "stripe_intent_id": s.stripeIntentId,
            "days_held": max(0, days_held),
            "created_at": s.createdAt,
            "buyer_or_client": client_summary,
            "seller_or_provider": provider_summary,
            "item_title": s.service.title if s.service else f"Service Application #{s.id}"
        })

    # Sort newest first
    combined_items.sort(key=lambda x: x["created_at"], reverse=True)
    
    total = len(combined_items)
    total_escrow_amount = sum(item["total_amount"] for item in combined_items)
    
    start_idx = (page - 1) * page_size
    paged_items = combined_items[start_idx:start_idx + page_size]

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_escrow_amount": round(total_escrow_amount, 2),
        "items": paged_items
    }

async def admin_force_release_order_escrow(order_id: int, admin_id: int = None):
    """
    Admin manually forces Escrow release directly to seller.
    """
    from app.modules.payments.service import capture_escrow_intent, transfer_to_connected_account
    from prisma.enums import OrderStatus

    order = await db.order.find_unique(
        where={"id": order_id},
        include={"product": {"include": {"seller": True}}}
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.paymentStatus == PaymentStatus.PAID:
        return {"status": "success", "message": "Order is already PAID and released"}

    if order.stripeIntentId:
        try:
            await capture_escrow_intent(order.stripeIntentId)
        except Exception as e:
            print(f"Warning on Stripe capture during admin force release: {e}")

    # Transfer earnings to seller
    seller = order.product.seller if (order.product and order.product.seller) else None
    if seller and seller.stripeAccountId and seller.payoutsEnabled:
        try:
            await transfer_to_connected_account(
                amount=order.subTotal,
                destination_account_id=seller.stripeAccountId,
                transfer_group=f"ADMIN_RELEASE_ORDER_{order.id}"
            )
        except Exception as e:
            print(f"Warning on seller transfer during admin force release: {e}")

    updated = await db.order.update(
        where={"id": order_id},
        data={
            "paymentStatus": PaymentStatus.PAID,
            "status": OrderStatus.DELIVERED,
            "tracking": {"create": [{"status": "ESCROW FORCE RELEASED BY ADMIN"}]}
        }
    )
    return {
        "status": "success",
        "message": f"Escrow for Order #{order_id} was successfully force released to seller",
        "order": updated
    }

async def admin_force_refund_order_escrow(order_id: int, reason: str = "Admin Escrow Refund"):
    """
    Admin cancels Escrow and refunds the buyer in full.
    """
    return await admin_process_refund(order_id=order_id, reason=reason)

async def admin_force_release_service_escrow(service_app_id: int, admin_id: int = None):
    """
    Admin manually forces Escrow release to Service Provider/Applicant.
    """
    from app.modules.payments.service import capture_escrow_intent, transfer_to_connected_account

    service_app = await db.serviceapplication.find_unique(
        where={"id": service_app_id},
        include={"client": True, "service": True}
    )
    if not service_app:
        raise HTTPException(status_code=404, detail="Service application not found")
    if service_app.paymentStatus == PaymentStatus.PAID:
        return {"status": "success", "message": "Service application is already PAID and released"}

    if service_app.stripeIntentId:
        try:
            await capture_escrow_intent(service_app.stripeIntentId)
        except Exception as e:
            print(f"Warning on Stripe capture during admin service release: {e}")

    applicant = service_app.client
    if applicant and applicant.stripeAccountId and applicant.payoutsEnabled:
        try:
            await transfer_to_connected_account(
                amount=service_app.subTotal,
                destination_account_id=applicant.stripeAccountId,
                transfer_group=f"ADMIN_RELEASE_SVC_{service_app.id}"
            )
        except Exception as e:
            print(f"Warning on applicant transfer during admin service release: {e}")

    updated = await db.serviceapplication.update(
        where={"id": service_app_id},
        data={
            "paymentStatus": PaymentStatus.PAID,
            "status": "COMPLETED"
        }
    )
    return {
        "status": "success",
        "message": f"Escrow for Service App #{service_app_id} was successfully force released",
        "service_application": updated
    }

async def admin_force_refund_service_escrow(service_app_id: int, reason: str = "Admin Service Escrow Refund"):
    """
    Admin cancels Escrow and refunds the Service Client in full.
    """
    return await admin_process_refund(service_application_id=service_app_id, reason=reason)

