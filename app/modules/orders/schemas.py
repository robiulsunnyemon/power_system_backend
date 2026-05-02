from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime
from prisma.enums import OrderStatus
from app.modules.products.schemas import ProductResponse
from enum import Enum

class OrderStatusFilter(str, Enum):
    ALL = "ALL"
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    CANCELLED = "CANCELLED"
    DELIVERED = "DELIVERED"

class OrderCreate(BaseModel):
    product_id: int

class OrderStatusUpdate(BaseModel):
    status: OrderStatus

class BuyerInfo(BaseModel):
    id: int
    fullname: str
    email: EmailStr
    profile_image: Optional[str] = None

class OrderTrackingResponse(BaseModel):
    id: int
    status: str
    createdAt: datetime

class OrderResponse(BaseModel):
    id: int
    status: OrderStatus
    createdAt: datetime
    updatedAt: datetime
    userId: int
    productId: int
    product: Optional[ProductResponse] = None
    user: Optional[BuyerInfo] = None
    tracking: List[OrderTrackingResponse] = []

    class Config:
        from_attributes = True

class ProductOrdersResponse(BaseModel):
    total_order: int
    total_accept_order: int
    total_pending_order: int
    orders: List[OrderResponse]
