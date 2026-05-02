from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import List, Optional, Annotated
from app.modules.products import service, schemas
from app.modules.users.router import get_current_user_id
from app.core.db import db
from prisma.enums import ProductCondition

router = APIRouter(tags=["Products & Categories"])

async def check_seller_role(user_id: int = Depends(get_current_user_id)):
    """
    Dependency to verify if the user has the SELLER role.
    """
    user = await db.user.find_unique(where={"id": user_id})
    if not user or user.role != "SELLER":
        raise HTTPException(
            status_code=403, 
            detail="Only sellers can perform this action"
        )
    return user_id

@router.post("/products/upload-images", response_model=schemas.ImageUploadResponse)
async def upload_images(
    images: list[UploadFile] = File(...),
    seller_id: int = Depends(check_seller_role)
):
    """
    Step 1: Upload images and get their URLs.
    """
    return await service.upload_product_images(images)

@router.post("/products", response_model=schemas.ProductResponse)
async def create_product(
    data: schemas.ProductCreate,
    seller_id: int = Depends(check_seller_role)
):
    """
    Step 2: Create product using the image URLs.
    """
    return await service.create_product(seller_id, data)

@router.get("/products/my", response_model=schemas.SellerProductsResponse)
async def get_my_products(
    status: schemas.ProductStatusFilter = schemas.ProductStatusFilter.ALL,
    seller_id: int = Depends(check_seller_role)
):
    """
    Endpoint for sellers to see their own products with status counts and filtering.
    """
    return await service.get_seller_products(seller_id, status)

@router.get("/products", response_model=List[schemas.ProductResponse])
async def list_products(category: str = "ALL"):
    """
    Public endpoint to list all active products with category filtering.
    """
    return await service.get_all_products(category)

@router.get("/categories", response_model=List[schemas.CategoryResponse])
async def list_categories():
    """
    Public endpoint to list all available categories.
    """
    return await service.get_all_categories()

@router.delete("/products/{product_id}")
async def delete_product(
    product_id: int,
    hard_delete: bool = False,
    seller_id: int = Depends(check_seller_role)
):
    """
    Endpoint for sellers to delete their product.
    - default: soft delete (status = DELETED)
    - hard_delete=true: permanent removal
    """
    return await service.delete_product(seller_id, product_id, hard_delete)
