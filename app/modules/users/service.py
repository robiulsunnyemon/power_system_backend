from app.core.db import db
from app.modules.users.schemas import UpdateProfileRequest

async def get_user_profile(user_id: int):
    return await db.user.find_unique(where={"id": user_id})

async def update_user_profile(user_id: int, data: UpdateProfileRequest):
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    return await db.user.update(
        where={"id": user_id},
        data=update_data
    )
