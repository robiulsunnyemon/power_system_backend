from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class ReviewCreate(BaseModel):
    order_id: int
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None
    images: List[str] = []

class ImageUploadResponse(BaseModel):
    urls: List[str]

class ReviewResponse(BaseModel):
    id: int
    rating: int
    comment: Optional[str]
    images: List[str]
    createdAt: datetime
    buyerId: int
    sellerId: int
    productId: int
    orderId: int

    class Config:
        from_attributes = True
