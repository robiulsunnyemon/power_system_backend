import firebase_admin
from firebase_admin import credentials, messaging
from app.core.db import db
from app.core.config import get_settings
from typing import Optional
import os
import json
import base64

settings = get_settings()

# Initialize Firebase Admin
try:
    firebase_admin.get_app()
except ValueError:
    try:
        if settings.FIREBASE_CREDENTIALS_BASE64:
            cred_dict = json.loads(base64.b64decode(settings.FIREBASE_CREDENTIALS_BASE64).decode('utf-8'))
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
        elif settings.FIREBASE_CREDENTIALS_PATH and os.path.exists(settings.FIREBASE_CREDENTIALS_PATH):
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
            firebase_admin.initialize_app(cred)
        else:
            # Fallback to default credentials (GOOGLE_APPLICATION_CREDENTIALS)
            firebase_admin.initialize_app()
    except Exception as e:
        print(f"Firebase initialization warning: {e}")

async def send_notification(
    user_id: int,
    title: str,
    description: str,
    notification_type: str, # 'order', 'service', 'new_service', 'message'
    image: Optional[str] = None,
    push_only: bool = False
):
    """
    Sends a notification to a user.
    - Saves in-app notification to DB (unless push_only=True)
    - Sends push notification via FCM based on user settings.
    """
    # 1. Save to DB (In-App Notification) - unless push_only is True
    if not push_only:
        await db.notification.create(
            data={
                "userId": user_id,
                "title": title,
                "description": description,
                "image": image
            }
        )
    
    # 2. Get User and Settings
    user = await db.user.find_unique(
        where={"id": user_id},
        include={"notificationSettings": True}
    )
    
    if not user or not user.fcmToken:
        return
    
    # Setting mapping
    settings_map = {
        "order": "orderUpdates",
        "service": "serviceUpdates",
        "new_service": "newServiceAlerts",
        "message": "messageNotifications"
    }
    
    setting_field = settings_map.get(notification_type)
    should_send_push = True
    
    if user.notificationSettings and setting_field:
        should_send_push = getattr(user.notificationSettings, setting_field, True)
    
    if not should_send_push:
        return

    # 3. Send Push Notification via FCM
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=description,
                image=image
            ),
            token=user.fcmToken,
            data={
                "type": notification_type
            }
        )
        response = messaging.send(message)
        return response
    except Exception as e:
        print(f"Error sending FCM to user {user_id}: {e}")
        return None

async def get_user_notifications(user_id: int, page: int = 1, page_size: int = 20):
    """
    Fetches in-app notifications for a user with pagination.
    """
    skip = (page - 1) * page_size
    notifications = await db.notification.find_many(
        where={"userId": user_id},
        order={"createdAt": "desc"},
        skip=skip,
        take=page_size
    )
    total = await db.notification.count(where={"userId": user_id})
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "notifications": notifications
    }

async def mark_as_read(user_id: int, notification_id: int):
    """
    Marks a specific notification as read.
    """
    return await db.notification.update_many(
        where={"id": notification_id, "userId": user_id},
        data={"isRead": True}
    )

async def update_notification_settings(user_id: int, settings_data: dict):
    """
    Updates or creates notification settings for a user.
    """
    return await db.notificationsetting.upsert(
        where={"userId": user_id},
        data={
            "create": {"userId": user_id, **settings_data},
            "update": settings_data
        }
    )

async def update_fcm_token(user_id: int, fcm_token: str):
    """
    Updates the user's FCM token.
    """
    return await db.user.update(
        where={"id": user_id},
        data={"fcmToken": fcm_token}
    )
