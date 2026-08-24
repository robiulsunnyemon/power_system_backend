from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from prisma.enums import SettingType

class SettingCreate(BaseModel):
    title: SettingType
    content: str

class MaintenanceModeToggle(BaseModel):
    is_maintenance: bool

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

class ServiceChargesResponse(BaseModel):
    platform_charge: float
    priority_charge: float

class ServiceChargesUpdate(BaseModel):
    platform_charge: Optional[float] = None
    priority_charge: Optional[float] = None

class PriorityFeesResponse(BaseModel):
    product_priority_fee: float
    service_priority_fee: float
    urgent_job_priority_fee: float
    priority_duration_hours: int

class PriorityFeesUpdate(BaseModel):
    product_priority_fee: Optional[float] = None
    service_priority_fee: Optional[float] = None
    urgent_job_priority_fee: Optional[float] = None
    priority_duration_hours: Optional[int] = None

