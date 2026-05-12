from app.core.db import db
from app.modules.messages.schemas import MessageCreate
from fastapi import UploadFile, HTTPException
from app.common.cloudinary import upload_image
from typing import List

async def save_message(sender_id: int, data: MessageCreate):
    """
    Saves a message to the database.
    """
    message = await db.message.create(
        data={
            "content": data.content,
            "type": data.type,
            "fileUrl": data.fileUrl,
            "senderId": sender_id,
            "receiverId": data.receiverId,
            "replyToId": data.replyToId
        },
        include={"sender": True}
    )
    
    # Notify Receiver (Push Only)
    from app.modules.notifications.service import send_notification
    sender_name = message.sender.fullname
    content_preview = message.content[:50] + "..." if len(message.content) > 50 else message.content
    
    await send_notification(
        user_id=data.receiverId,
        title=f"New message from {sender_name}",
        description=content_preview if message.type == "TEXT" else "Sent a file",
        notification_type="message",
        push_only=True
    )
    
    return message

async def get_conversations(user_id: int):
    """
    Fetches a list of conversations for the user.
    Each conversation includes the last message and unread count.
    """
    # 1. Get all messages where the user is either sender or receiver
    # This is a bit complex in Prisma without raw SQL for grouping by conversation partner.
    # We'll fetch the messages and group them in Python for simplicity in this small app.
    messages = await db.message.find_many(
        where={
            "OR": [
                {"senderId": user_id},
                {"receiverId": user_id}
            ]
        },
        include={
            "sender": {"include": {"profile": True}},
            "receiver": {"include": {"profile": True}}
        },
        order={"createdAt": "desc"}
    )

    conversations_dict = {}
    
    for msg in messages:
        # Determine the other user in the conversation
        other_user = msg.receiver if msg.senderId == user_id else msg.sender
        other_id = other_user.id
        
        if other_id not in conversations_dict:
            # First time seeing this conversation partner (since we ordered by desc, this is the latest message)
            unread_count = await db.message.count(
                where={
                    "senderId": other_id,
                    "receiverId": user_id,
                    "isRead": False
                }
            )
            
            conversations_dict[other_id] = {
                "other_user_id": other_id,
                "other_user_name": other_user.fullname,
                "other_user_image": other_user.profile.profile_image if other_user.profile else None,
                "last_message": msg.content if msg.type == "TEXT" else "[File]",
                "last_message_time": msg.createdAt,
                "unread_count": unread_count
            }
            
    return list(conversations_dict.values())

async def get_chat_history(user_id: int, other_user_id: int):
    """
    Fetches the full chat history between two users.
    """
    messages = await db.message.find_many(
        where={
            "OR": [
                {"senderId": user_id, "receiverId": other_user_id},
                {"senderId": other_user_id, "receiverId": user_id}
            ]
        },
        order={"createdAt": "asc"}
    )
    return messages

async def mark_messages_as_read(receiver_id: int, sender_id: int):
    """
    Marks all messages from a specific sender to the current user as read.
    """
    await db.message.update_many(
        where={
            "senderId": sender_id,
            "receiverId": receiver_id,
            "isRead": False
        },
        data={"isRead": True}
    )
    return {"status": "success"}

async def upload_message_file(file: UploadFile):
    """
    Uploads a file for messaging.
    """
    result = await upload_image(file, folder="jorden/messages")
    if not result:
        raise HTTPException(status_code=500, detail="File upload failed")
    return {"url": result.get("secure_url")}
