from pydantic import BaseModel
from typing import List, Optional

class CheckoutProductRequest(BaseModel):
    product_id: int
    distance_km: Optional[float] = 0.0
    delivery_addons: List[str] = []
    has_protection: bool = False
    is_escrow: bool = False
    is_cod: bool = False

class CheckoutServiceRequest(BaseModel):
    service_application_id: int
    has_protection: bool = False
    is_escrow: bool = False
    is_cod: bool = False

class RefundRequest(BaseModel):
    order_id: int
    amount: Optional[float] = None # full refund if none
    reason: Optional[str] = None

class CreateOnboardingLinkRequest(BaseModel):
    refresh_url: Optional[str] = "https://jordencuz.com/stripe/connect/refresh"
    return_url: Optional[str] = "https://jordencuz.com/stripe/connect/return"

class StripeConnectStatusResponse(BaseModel):
    stripe_account_id: Optional[str] = None
    stripe_account_status: str
    payouts_enabled: bool
    charges_enabled: bool

class OnboardingLinkResponse(BaseModel):
    onboarding_url: str
    stripe_account_id: str

class PriorityBoostProductRequest(BaseModel):
    product_id: int

class PriorityBoostServiceRequest(BaseModel):
    service_id: int

class PriorityBoostUrgentJobRequest(BaseModel):
    service_application_id: int

