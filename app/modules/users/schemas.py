from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserProfileResponse(BaseModel):
    id: int
    fullname: str
    email: EmailStr
    isVerified: bool
    accountStatus: str
    role: str
    displayname: Optional[str] = None
    bio: Optional[str] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    createdAt: datetime
    updatedAt: datetime

class UpdateProfileRequest(BaseModel):
    fullname: Optional[str] = None
    displayname: Optional[str] = None
    bio: Optional[str] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None
