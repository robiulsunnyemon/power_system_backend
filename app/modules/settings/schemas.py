from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from prisma.enums import SettingType

class SettingCreate(BaseModel):
    title: SettingType
    content: str

class SettingUpdate(BaseModel):
    #title: Optional[SettingType] = None
    content: Optional[str] = None

class SettingResponse(BaseModel):
    id: int
    title: SettingType
    content: str
    createdAt: datetime
    updatedAt: datetime

    class Config:
        from_attributes = True
