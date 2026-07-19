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
