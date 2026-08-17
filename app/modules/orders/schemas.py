from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime
from prisma.enums import OrderStatus, PaymentMethod, PaymentStatus
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
    
    # Financials
    subTotal: float = 0
    platformFee: float = 0
    protectionFee: float = 0
    escrowFee: float = 0
    deliveryFee: float = 0
    deliveryAddonFee: float = 0
    totalAmount: float = 0
    
    # Payment Details
    paymentMethod: PaymentMethod = PaymentMethod.STRIPE
    paymentStatus: PaymentStatus = PaymentStatus.PENDING
    stripeIntentId: Optional[str] = None
    
    # Delivery & Addons
    distanceKm: Optional[float] = None
    deliveryAddons: List[str] = []
    deliveryAddress: Optional[str] = None
    deliveryCity: Optional[str] = None
    recipientName: Optional[str] = None
    recipientPhone: Optional[str] = None
    deliveryInstructions: Optional[str] = None
    
    # Mechanics
    hasProtection: bool = False
    isEscrow: bool = False
    isCOD: bool = False

    createdAt: datetime
    updatedAt: datetime
    userId: int
    productId: int
    product: Optional[ProductResponse] = None
    user: Optional[BuyerInfo] = None
    tracking: List[OrderTrackingResponse] = []

    class Config:
        from_attributes = True

class PaginatedOrderResponse(BaseModel):
    total: int
    page: int
    page_size: int
    orders: List[OrderResponse]

class ProductOrdersResponse(BaseModel):
    total_order: int
    total_accept_order: int
    total_pending_order: int
    orders: List[OrderResponse]

class GrowthFilter(str, Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    SIX_MONTHS = "6months"
    YEARLY = "yearly"
    YEAR_RANGE = "year_range"

class RevenueGrowthDataPoint(BaseModel):
    label: str
    revenue: float

class RevenueGrowthResponse(BaseModel):
    data: List[RevenueGrowthDataPoint]

class SellerDashboardStats(BaseModel):
    total_revenue: float
    total_active_products: int
    total_pending_orders: int
    revenue_growth_pct: float
