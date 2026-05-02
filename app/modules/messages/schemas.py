from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from prisma.enums import MessageType

class MessageCreate(BaseModel):
    receiverId: int
    content: str
    type: MessageType = MessageType.TEXT
    fileUrl: Optional[str] = None
    replyToId: Optional[int] = None

class MessageResponse(BaseModel):
    id: int
    senderId: int
    receiverId: int
    content: str
    type: MessageType
    fileUrl: Optional[str]
    isRead: bool
    replyToId: Optional[int]
    createdAt: datetime

    class Config:
        from_attributes = True

class ConversationResponse(BaseModel):
    other_user_id: int
    other_user_name: str
    other_user_image: Optional[str]
    last_message: str
    last_message_time: datetime
    unread_count: int

class FileUploadResponse(BaseModel):
    url: str
