from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime
from enum import Enum
from prisma.enums import ApplicationStatus
from app.modules.products.schemas import SellerInfo

class ApplicationStatusFilter(str, Enum):
    ALL = "ALL"
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    COMPLETED = "COMPLETED"

class ProviderInfo(BaseModel):
    id: int
    fullname: str
    email: str
    displayname: Optional[str] = None
    profile_image: Optional[str] = None
    trust_score: float = 0
    badge: str = "New Member"

class ServiceInfo(BaseModel):
    id: int
    title: str
    price: float
    images: List[str]
    provider: Optional[ProviderInfo] = None

class ServiceApplicationCreate(BaseModel):
    proposedRate: float
    expectedStartDate: datetime
    coverLetter: str

class ApplicationTrackingResponse(BaseModel):
    id: int
    status: str
    createdAt: datetime

class ApplicationTrackingCreate(BaseModel):
    status: str

class ServiceApplicationResponse(BaseModel):
    id: int
    proposedRate: float
    expectedStartDate: datetime
    coverLetter: str
    status: ApplicationStatus
    createdAt: datetime
    updatedAt: datetime
    serviceId: int
    clientId: int
    service: ServiceInfo
    client: SellerInfo
    tracking: List[ApplicationTrackingResponse] = []

    class Config:
        from_attributes = True

class ServiceApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus

class EarningsQuickStats(BaseModel):
    this_week: float
    this_month: float
    total_completed_jobs: int

class EarningsHistoryItem(BaseModel):
    id: int
    title: str
    amount: float
    status: ApplicationStatus
    date: datetime
    images: List[str] = []

class ProviderEarningsResponse(BaseModel):
    total_earnings: float
    pending_earnings: float
    quick_stats: EarningsQuickStats
    history: List[EarningsHistoryItem]

class ProviderRequestsResponse(BaseModel):
    pending_count: int
    accepted_count: int
    declined_count: int
    completed_count: int
    requests: List[ServiceApplicationResponse]

