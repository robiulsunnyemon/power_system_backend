from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from prisma.enums import ProductCondition, ProductStatus

class CategoryResponse(BaseModel):
    id: int
    name: str

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

    class Config:
        from_attributes = True
