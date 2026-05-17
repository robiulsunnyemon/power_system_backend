from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from app.modules.products.schemas import SellerInfo

class ServiceReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="Rating must be between 1 and 5")
    comment: Optional[str] = Field(None, description="Optional comment/review for the provider")
    images: Optional[List[str]] = Field(default_factory=list, description="Optional list of image URLs")

class ServiceReviewResponse(BaseModel):
    id: int
    rating: int
    comment: Optional[str]
    images: List[str]
    createdAt: datetime
    applicationId: int
    clientId: int
    providerId: int
    client: Optional[SellerInfo] = None

    class Config:
        from_attributes = True

class ProviderStatsResponse(BaseModel):
    providerId: int
    totalRating: int
    averageRating: float
    totalReviews: int

    class Config:
        from_attributes = True
