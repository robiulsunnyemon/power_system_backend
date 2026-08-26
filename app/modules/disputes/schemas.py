from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from prisma.enums import DisputeReason, DisputeStatus, DisputeType

class CreateDisputeRequest(BaseModel):
    reason: DisputeReason
    description: str
    evidenceImages: Optional[List[str]] = []

class DisputePartySummary(BaseModel):
    id: int
    fullname: str
    email: str

class DisputeResponse(BaseModel):
    id: int
    disputeType: DisputeType
    reason: DisputeReason
    description: str
    evidenceImages: List[str]
    status: DisputeStatus
    adminNotes: Optional[str] = None
    orderId: Optional[int] = None
    order_title: Optional[str] = None
    order_amount: Optional[float] = None
    serviceApplicationId: Optional[int] = None
    service_title: Optional[str] = None
    service_amount: Optional[float] = None
    initiator: DisputePartySummary
    respondent: DisputePartySummary
    createdAt: datetime
    updatedAt: datetime

class PaginatedDisputeResponse(BaseModel):
    total: int
    page: int
    page_size: int
    disputes: List[DisputeResponse]

class ResolveDisputeRequest(BaseModel):
    status: DisputeStatus # RESOLVED_BUYER_REFUNDED, RESOLVED_SELLER_PAID, REJECTED, UNDER_REVIEW
    adminNotes: str
    execute_action: bool = True # Automatically trigger refund or escrow release
