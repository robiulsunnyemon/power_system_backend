from fastapi import APIRouter, Depends, Query, status
from app.modules.notifications import service, schemas
from app.modules.users.router import get_current_user_id
from app.core.db import db

router = APIRouter(prefix="/notifications", tags=["Notifications"])

@router.get("/", response_model=schemas.PaginatedNotificationResponse)
async def get_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: int = Depends(get_current_user_id)
):
    return await service.get_user_notifications(user_id, page, page_size)

@router.patch("/{notification_id}/read")
async def mark_as_read(
    notification_id: int,
    user_id: int = Depends(get_current_user_id)
):
    await service.mark_as_read(user_id, notification_id)
    return {"message": "Notification marked as read"}

@router.get("/settings", response_model=schemas.NotificationSettingsResponse)
async def get_settings(user_id: int = Depends(get_current_user_id)):
    settings = await db.notificationsetting.find_unique(where={"userId": user_id})
    if not settings:
        # Return defaults if not created yet
        return {
            "orderUpdates": True,
            "serviceUpdates": True,
            "newServiceAlerts": True,
            "messageNotifications": True
        }
    return settings

@router.put("/settings", response_model=schemas.NotificationSettingsResponse)
async def update_settings(
    data: schemas.NotificationSettingsUpdate,
    user_id: int = Depends(get_current_user_id)
):
    settings_data = {k: v for k, v in data.model_dump().items() if v is not None}
    return await service.update_notification_settings(user_id, settings_data)

@router.post("/fcm-token")
async def update_fcm_token(
    data: schemas.FCMTokenUpdate,
    user_id: int = Depends(get_current_user_id)
):
    await service.update_fcm_token(user_id, data.fcmToken)
    return {"message": "FCM token updated successfully"}
