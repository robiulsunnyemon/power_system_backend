from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, UploadFile, File
from typing import List
from app.modules.messages import service, schemas
from app.modules.users.router import get_current_user_id
from app.core.websocket import manager
from app.common.security import decode_token
import json

router = APIRouter(prefix="/messages", tags=["Messages"])

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = None):
    """
    WebSocket endpoint for real-time messaging with Token authentication.
    URL: ws://localhost:8000/messages/ws?token=YOUR_JWT_TOKEN
    """
    if not token:
        await websocket.close(code=1008)  # Policy Violation
        return

    payload = decode_token(token)
    if not payload:
        await websocket.close(code=1008)
        return

    user_id = int(payload.get("sub"))
    
    await manager.connect(user_id, websocket)
    try:
        while True:
            # Receive message from user
            data = await websocket.receive_text()
            try:
                message_data = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({"error": "Invalid JSON format. Please use double quotes."})
                continue
            
            try:
                # Format: {"receiverId": 2, "content": "Hello", "type": "TEXT", "fileUrl": null, "replyToId": null}
                msg_create = schemas.MessageCreate(**message_data)
            except Exception as e:
                await websocket.send_json({"error": f"Invalid data structure: {str(e)}"})
                continue
            
            # 1. Save to DB
            saved_msg = await service.save_message(user_id, msg_create)
            
            # 2. Prepare response
            response = {
                "id": saved_msg.id,
                "senderId": user_id,
                "receiverId": saved_msg.receiverId,
                "content": saved_msg.content,
                "type": saved_msg.type,
                "fileUrl": saved_msg.fileUrl,
                "isRead": saved_msg.isRead,
                "replyToId": saved_msg.replyToId,
                "createdAt": saved_msg.createdAt.isoformat()
            }
            
            # 3. Send to receiver if online
            await manager.send_personal_message(response, saved_msg.receiverId)
            
            # 4. Echo back to sender to confirm delivery/save
            await websocket.send_json(response)
            
    except WebSocketDisconnect:
        manager.disconnect(user_id)
    except Exception as e:
        print(f"WS Error: {e}")
        manager.disconnect(user_id)

@router.get("/conversations", response_model=List[schemas.ConversationResponse])
async def get_conversations(user_id: int = Depends(get_current_user_id)):
    """
    Returns a list of all conversations for the logged-in user.
    """
    return await service.get_conversations(user_id)

@router.get("/history/{other_user_id}", response_model=List[schemas.MessageResponse])
async def get_chat_history(other_user_id: int, user_id: int = Depends(get_current_user_id)):
    """
    Returns the full chat history between the current user and another user.
    """
    return await service.get_chat_history(user_id, other_user_id)

@router.patch("/read/{sender_id}")
async def mark_as_read(sender_id: int, user_id: int = Depends(get_current_user_id)):
    """
    Marks all unread messages from a specific sender as read.
    """
    return await service.mark_messages_as_read(user_id, sender_id)

@router.post("/upload-file", response_model=schemas.FileUploadResponse)
async def upload_file(file: UploadFile = File(...), user_id: int = Depends(get_current_user_id)):
    """
    Uploads a file (image, document, etc.) to be used in messaging.
    """
    return await service.upload_message_file(file)
