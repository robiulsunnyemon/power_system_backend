from pydantic import BaseModel
from typing import List, Optional
from enum import Enum
from datetime import datetime
from prisma.enums import ProductCondition, ProductStatus, ItemSize

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
    badge: Optional[str] = "New Member"
    avg_rating: float = 0.0
    total_reviews: int = 0

class ProductCreate(BaseModel):
    title: str
    description: str
    category: str  # Category name
    price: float
    tax_fee: Optional[float] = 0
    delivery_fee: Optional[float] = 0
    condition: ProductCondition
    images: List[str]  # List of Cloudinary URLs
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    itemSize: ItemSize = ItemSize.SMALL

class ImageUploadResponse(BaseModel):
    urls: List[str]

class ProductResponse(BaseModel):
    id: int
    title: str
    description: str
    images: List[str]
    price: float
    tax_fee: Optional[float] = 0
    delivery_fee: Optional[float] = 0
    total_fee: float
    condition: ProductCondition
    status: ProductStatus
    isPriority: bool = False
    priorityExpiresAt: Optional[datetime] = None
    itemSize: ItemSize = ItemSize.SMALL
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    createdAt: datetime
    updatedAt: datetime
    sellerId: int
    category: CategoryResponse
    seller: SellerInfo
    pending_orders_count: Optional[int] = 0
    delivered_orders_count: Optional[int] = 0

    class Config:
        from_attributes = True

class SellerProductsResponse(BaseModel):
    total_products: int
    total_active: int
    total_draft: int
    total_inactive: int
    total_deleted: int
    total_soldout: int

class PaginatedSellerProductsResponse(BaseModel):
    total: int
    page: int
    page_size: int
    counts: SellerProductsResponse
    products: List[ProductResponse]

class PaginatedProductResponse(BaseModel):
    total: int
    page: int
    page_size: int
    products: List[ProductResponse]

class ProductUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    tax_fee: Optional[float] = None
    delivery_fee: Optional[float] = None
    condition: Optional[ProductCondition] = None
    status: Optional[ProductStatus] = None
    category: Optional[str] = None
    images: Optional[List[str]] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None
