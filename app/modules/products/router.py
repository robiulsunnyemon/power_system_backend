from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form,Query
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
    if not user or "SELLER" not in user.roles:
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

@router.get("/products/my", response_model=schemas.PaginatedSellerProductsResponse)
async def get_my_products(
    product_id: Optional[int] = Query(None, description="Optional: Filter by a specific product ID"),
    status: schemas.ProductStatusFilter = schemas.ProductStatusFilter.ALL,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    seller_id: int = Depends(check_seller_role)
):
    """
    Endpoint for sellers to see their own products with status counts, filtering and pagination.
    """
    return await service.get_seller_products(seller_id, status, product_id, page, page_size)

@router.get("/products", response_model=schemas.PaginatedProductResponse)
async def list_products(
    product_id: Optional[int] = Query(None, description="Optional: Filter by a specific product ID"),
    category: str = "ALL",
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100)
):
    """
    Public endpoint to list all active products with category filtering and pagination.
    """
    return await service.get_all_products(category, product_id, page, page_size)

@router.get("/products/search", response_model=schemas.PaginatedProductResponse)
async def search_products_endpoint(
    query: Optional[str] = Query(None, description="Search query string (matches any word in title or description)"),
    category_id: Optional[int] = Query(None, description="Optional Category ID to filter products"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100)
):
    """
    Public search endpoint to search active products matching keywords in title or description,
    optionally filtered by Category ID, with pagination.
    """
    return await service.search_products(query, category_id, page, page_size)

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
