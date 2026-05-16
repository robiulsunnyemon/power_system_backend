from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from app.modules.products.schemas import ProductResponse
from app.modules.reviews.schemas import ReviewResponse

class SellerProfileInfo(BaseModel):
    id: int
    fullname: str
    displayname: Optional[str] = None
    profile_image: Optional[str] = None
    raw_score: float
    trust_score: float
    badge: str
    total_delivery: int
    average_rating: float
    positive: float
    is_online: bool = False

class SellerPublicProfileResponse(BaseModel):
    seller: SellerProfileInfo
    active_products: List[ProductResponse]
    reviews: List[ReviewResponse]

class UserProfileResponse(BaseModel):
    id: int
    fullname: str
    email: EmailStr
    isVerified: bool
    accountStatus: str
    roles: List[str]
    displayname: Optional[str] = None
    bio: Optional[str] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    profile_image: Optional[str] = None
    trust_score: float = 0.0
    raw_score: float = 0.0
    is_online: bool = False
    createdAt: datetime
    updatedAt: datetime

class UpdateProfileRequest(BaseModel):
    fullname: Optional[str] = None
    displayname: Optional[str] = None
    bio: Optional[str] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None

class DeleteAccountRequest(BaseModel):
    password: str

class UserSummaryResponse(BaseModel):
    listings: int
    jobs_completed: int
    trust_score: float

