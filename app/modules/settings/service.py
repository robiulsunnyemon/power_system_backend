from app.core.db import db
from fastapi import HTTPException
from app.modules.settings.schemas import SettingCreate, SettingUpdate, MaintenanceModeToggle
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

async def toggle_maintenance_mode(data: MaintenanceModeToggle):
    """
    Toggles the maintenance mode setting.
    """
    content_value = "true" if data.is_maintenance else "false"
    
    # Check if a setting with this title already exists
    setting = await db.setting.find_unique(where={"title": SettingType.MAINTENANCE_MODE})
    
    if setting:
        return await db.setting.update(
            where={"id": setting.id},
            data={"content": content_value}
        )
    else:
        return await db.setting.create(
            data={
                "title": SettingType.MAINTENANCE_MODE,
                "content": content_value
            }
        )

async def is_maintenance_mode_active() -> bool:
    """
    Checks if maintenance mode is active.
    """
    try:
        setting = await db.setting.find_unique(where={"title": SettingType.MAINTENANCE_MODE})
        return setting is not None and setting.content == "true"
    except Exception:
        return False

async def get_service_charges():
    """
    Fetches the configured platform and priority charges for service creation.
    Defaults: Platform Charge = $10.0, Priority Charge = $5.0.
    """
    platform_setting = await db.setting.find_unique(where={"title": SettingType.SERVICE_PLATFORM_CHARGE})
    priority_setting = await db.setting.find_unique(where={"title": SettingType.SERVICE_PRIORITY_CHARGE})

    try:
        platform_charge = float(platform_setting.content) if platform_setting and platform_setting.content else 10.0
    except (ValueError, TypeError):
        platform_charge = 10.0

    try:
        priority_charge = float(priority_setting.content) if priority_setting and priority_setting.content else 5.0
    except (ValueError, TypeError):
        priority_charge = 5.0

    return {
        "platform_charge": platform_charge,
        "priority_charge": priority_charge
    }

async def update_service_charges(data):
    """
    Admin only: Updates or creates the platform and priority charge settings.
    """
    if data.platform_charge is not None:
        platform_val = str(data.platform_charge)
        existing_platform = await db.setting.find_unique(where={"title": SettingType.SERVICE_PLATFORM_CHARGE})
        if existing_platform:
            await db.setting.update(
                where={"id": existing_platform.id},
                data={"content": platform_val}
            )
        else:
            await db.setting.create(
                data={
                    "title": SettingType.SERVICE_PLATFORM_CHARGE,
                    "content": platform_val
                }
            )

    if data.priority_charge is not None:
        priority_val = str(data.priority_charge)
        existing_priority = await db.setting.find_unique(where={"title": SettingType.SERVICE_PRIORITY_CHARGE})
        if existing_priority:
            await db.setting.update(
                where={"id": existing_priority.id},
                data={"content": priority_val}
            )
        else:
            await db.setting.create(
                data={
                    "title": SettingType.SERVICE_PRIORITY_CHARGE,
                    "content": priority_val
                }
            )

    return await get_service_charges()

