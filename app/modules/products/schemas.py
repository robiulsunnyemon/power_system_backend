from pydantic import BaseModel
from typing import List, Optional
from enum import Enum
from datetime import datetime
from prisma.enums import ProductCondition, ProductStatus

class ProductStatusFilter(str, Enum):
    ALL = "ALL"
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    DELETED = "DELETED"
    INACTIVE = "INACTIVE"
    SOLDOUT = "SOLDOUT"

class CategoryResponse(BaseModel):
    id: int
    name: str

class SellerInfo(BaseModel):
    id: int
    fullname: str
    email: str
    displayname: Optional[str] = None
    profile_image: Optional[str] = None

class ProductCreate(BaseModel):
    title: str
    description: str
    category: str  # Category name
    price: float
    condition: ProductCondition
    images: List[str]  # List of Cloudinary URLs
    longitude: Optional[float] = None
    latitude: Optional[float] = None

class ImageUploadResponse(BaseModel):
    urls: List[str]

class ProductResponse(BaseModel):
    id: int
    title: str
    description: str
    images: List[str]
    price: float
    condition: ProductCondition
    status: ProductStatus
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    createdAt: datetime
    updatedAt: datetime
    sellerId: int
    category: CategoryResponse
    seller: SellerInfo

    class Config:
        from_attributes = True

class SellerProductsResponse(BaseModel):
    total_products: int
    total_active: int
    total_draft: int
    total_inactive: int
    total_deleted: int
    total_soldout: int
    products: List[ProductResponse]
