from pydantic import BaseModel
from enum import Enum
from typing import List, Optional, Any
from datetime import datetime
from prisma.enums import AccountStatus, TransactionType, TransactionStatus, PaymentStatus, PaymentMethod

from app.modules.users.schemas import UserProfileResponse

class UserRoleFilter(str, Enum):
    ALL = "ALL"
    USER = "USER"
    SELLER = "SELLER"
    SERVICE_PROVIDER = "SERVICE_PROVIDER"
    ADMIN = "ADMIN"

class PaginatedUserResponse(BaseModel):
    total: int
    page: int
    page_size: int
    users: List[UserProfileResponse]

class UpdateStatusRequest(BaseModel):
    accountStatus: AccountStatus

class DashboardStatsResponse(BaseModel):
    total_users: int
    active_users: int
    pending_users: int
    total_growth_pct: float
    active_growth_pct: float
    pending_growth_pct: float
    total_platform_revenue: float = 0.0
    total_transaction_volume: float = 0.0
    active_stripe_users: int = 0

class GrowthDataPoint(BaseModel):
    label: str # e.g. "Mon", "May", "2024"
    count: int

class GrowthResponse(BaseModel):
    data: List[GrowthDataPoint]

class GrowthFilter(str, Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    SIX_MONTHS = "6months"
    YEARLY = "yearly"
    YEAR_RANGE = "year_range"

# --- Payment Monitoring & Financial Analytics ---
class RevenueTrendPoint(BaseModel):
    date: str
    revenue: float
    volume: float
    transaction_count: int

class PaymentChannelBreakdown(BaseModel):
    product_revenue: float
    product_volume: float
    service_revenue: float
    service_volume: float
    priority_boost_revenue: float

class PaymentMethodDistribution(BaseModel):
    stripe_volume: float
    stripe_count: int
    cod_volume: float
    cod_count: int

class PaymentOverviewResponse(BaseModel):
    total_platform_revenue: float
    total_transaction_volume: float
    total_escrow_held_volume: float
    total_refund_volume: float
    active_stripe_connect_sellers: int
    channel_breakdown: PaymentChannelBreakdown
    payment_method_distribution: PaymentMethodDistribution
    revenue_trend: List[RevenueTrendPoint]

# --- Transaction Management ---
class TransactionUserSummary(BaseModel):
    id: int
    fullname: str
    email: str

class TransactionItem(BaseModel):
    id: int
    amount: float
    currency: str
    type: TransactionType
    status: TransactionStatus
    stripeChargeId: Optional[str] = None
    createdAt: datetime
    updatedAt: datetime
    user: TransactionUserSummary
    orderId: Optional[int] = None
    order_details: Optional[dict] = None
    serviceApplicationId: Optional[int] = None
    service_details: Optional[dict] = None

class PaginatedTransactionResponse(BaseModel):
    total: int
    page: int
    page_size: int
    transactions: List[TransactionItem]

# --- Refund Management ---
class AdminProcessRefundRequest(BaseModel):
    order_id: Optional[int] = None
    service_application_id: Optional[int] = None
    amount: Optional[float] = None
    reason: str

class AdminRefundItem(BaseModel):
    transaction_id: int
    amount: float
    currency: str
    createdAt: datetime
    user: TransactionUserSummary
    order_id: Optional[int] = None
    service_application_id: Optional[int] = None
    stripe_charge_id: Optional[str] = None
    title: str

class PaginatedRefundResponse(BaseModel):
    total: int
    page: int
    page_size: int
    refunds: List[AdminRefundItem]

# --- Escrow Release Controls ---
class EscrowItemResponse(BaseModel):
    type: str # "ORDER" or "SERVICE"
    id: int # orderId or serviceAppId
    subtotal: float
    platform_fee: float
    protection_fee: float
    escrow_fee: float
    total_amount: float
    payment_status: str
    stripe_intent_id: Optional[str] = None
    days_held: int
    created_at: datetime
    buyer_or_client: TransactionUserSummary
    seller_or_provider: Optional[TransactionUserSummary] = None
    item_title: str

class PaginatedEscrowListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_escrow_amount: float
    items: List[EscrowItemResponse]

class AdminEscrowActionRequest(BaseModel):
    reason: Optional[str] = "Admin manual action"
