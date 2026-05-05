from app.core.db import db
from prisma.enums import Role
from app.modules.admin.schemas import UserRoleFilter
from fastapi import HTTPException

async def get_all_users(role_filter: UserRoleFilter):
    """
    Fetches all users with their profile data, optionally filtered by role.
    """
    query = {}
    if role_filter != UserRoleFilter.ALL:
        # Map the filter enum to the Prisma Role enum
        query["roles"] = {"has": Role(role_filter.value)}
    
    users = await db.user.find_many(
        where=query,
        include={"profile": True}
    )
    
    # Flatten the profile_image into the response format
    result = []
    for user in users:
        user_dict = user.model_dump()
        user_dict["profile_image"] = user.profile.profile_image if user.profile else None
        result.append(user_dict)
    
    return result

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
    return user_dict
