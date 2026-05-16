from app.core.db import db
from prisma.enums import Role, AccountStatus
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
    user_dict["is_online"] = manager.is_user_online(user_id)
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

    return {
        "total_users": total_users,
        "active_users": active_users,
        "pending_users": pending_users,
        "total_growth_pct": calculate_growth_pct(new_this_month, new_last_month),
        "active_growth_pct": calculate_growth_pct(active_new_this_month, active_new_last_month),
        "pending_growth_pct": calculate_growth_pct(pending_new_this_month, pending_new_last_month)
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
