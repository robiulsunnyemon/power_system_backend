from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class AllowedLocationBase(BaseModel):
    name: str
    state: str = "WA"
    country: str = "Australia"
    latitude: float
    longitude: float
    radiusKm: float = 60.0
    isActive: bool = True

class AllowedLocationCreate(AllowedLocationBase):
    pass

class AllowedLocationUpdate(BaseModel):
    name: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radiusKm: Optional[float] = None
    isActive: Optional[bool] = None

class AllowedLocationResponse(BaseModel):
    id: int
    name: str
    state: str
    country: str
    latitude: float
    longitude: float
    radiusKm: float
    isActive: bool
    createdAt: datetime
    updatedAt: datetime

    class Config:
        from_attributes = True

class PaginatedAllowedLocationResponse(BaseModel):
    total: int
    items: List[AllowedLocationResponse]

class ValidateLocationRequest(BaseModel):
    latitude: float
    longitude: float
    address: Optional[str] = None

class ValidateLocationResponse(BaseModel):
    is_allowed: bool
    matched_location: Optional[str] = None
    message: str
