from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class NotificationResponse(BaseModel):
    id: int
    title: str
    description: str
    image: Optional[str] = None
    isRead: bool
    createdAt: datetime

class PaginatedNotificationResponse(BaseModel):
    total: int
    page: int
    page_size: int
    notifications: List[NotificationResponse]

class NotificationSettingsUpdate(BaseModel):
    orderUpdates: Optional[bool] = None
    serviceUpdates: Optional[bool] = None
    newServiceAlerts: Optional[bool] = None
    messageNotifications: Optional[bool] = None

class NotificationSettingsResponse(BaseModel):
    orderUpdates: bool
    serviceUpdates: bool
    newServiceAlerts: bool
    messageNotifications: bool

class FCMTokenUpdate(BaseModel):
    fcmToken: str
