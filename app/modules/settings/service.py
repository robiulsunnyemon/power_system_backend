from app.core.db import db
from fastapi import HTTPException
from app.modules.settings.schemas import SettingCreate, SettingUpdate
from prisma.enums import SettingType

async def create_setting(data: SettingCreate):
    """
    Creates a new setting entry.
    """
    # Check if a setting with this title already exists (since it's unique)
    existing = await db.setting.find_unique(where={"title": data.title})
    if existing:
        raise HTTPException(status_code=400, detail=f"Setting for {data.title} already exists. Use update instead.")
        
    return await db.setting.create(
        data={
            "title": data.title,
            "content": data.content
        }
    )

async def get_settings(title: SettingType = None):
    """
    Fetches all settings or filters by title.
    """
    if title:
        setting = await db.setting.find_unique(where={"title": title})
        return [setting] if setting else []
    
    return await db.setting.find_many(order={"createdAt": "desc"})

async def get_setting_by_id(setting_id: int):
    """
    Fetches a single setting by ID.
    """
    setting = await db.setting.find_unique(where={"id": setting_id})
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    return setting

async def update_setting(setting_id: int, data: SettingUpdate):
    """
    Updates an existing setting.
    """
    # Check if exists
    setting = await db.setting.find_unique(where={"id": setting_id})
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
        
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    
    # If title is being updated, check uniqueness
    if "title" in update_data and update_data["title"] != setting.title:
        existing = await db.setting.find_unique(where={"title": update_data["title"]})
        if existing:
            raise HTTPException(status_code=400, detail=f"Setting for {update_data['title']} already exists.")

    return await db.setting.update(
        where={"id": setting_id},
        data=update_data
    )

async def delete_setting(setting_id: int):
    """
    Deletes a setting entry.
    """
    setting = await db.setting.find_unique(where={"id": setting_id})
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
        
    await db.setting.delete(where={"id": setting_id})
    return {"message": "Setting deleted successfully"}
