from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime
from prisma.enums import PricingType, ServiceStatus
from app.modules.products.schemas import CategoryResponse, SellerInfo

class Requirement(BaseModel):
    title: str
    description: str

class ServiceCreate(BaseModel):
    title: str
    description: str
    category: str  # Category name
    price: float
    pricingType: PricingType = PricingType.FIXED
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    requirements: Optional[List[Requirement]] = None
    availability: Optional[List[str]] = None
    images: List[str]
    status: ServiceStatus = ServiceStatus.DRAFT

class ServiceUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    pricingType: Optional[PricingType] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    requirements: Optional[List[Requirement]] = None
    availability: Optional[List[str]] = None
    images: Optional[List[str]] = None
    status: Optional[ServiceStatus] = None

class ServiceResponse(BaseModel):
    id: int
    title: str
    description: str
    price: float
    pricingType: PricingType
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    requirements: Optional[Any] = None
    availability: Optional[Any] = None
    images: List[str]
    status: ServiceStatus
    createdAt: datetime
    updatedAt: datetime
    providerId: int
    category: Optional[str] = None
    provider: SellerInfo

    class Config:
        from_attributes = True

class ServiceListResponse(BaseModel):
    total_services: int
    total_active: int
    total_draft: int
    services: List[ServiceResponse]

class PaginatedServiceResponse(BaseModel):
    total: int
    page: int
    page_size: int
    services: List[ServiceResponse]
