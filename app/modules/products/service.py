from app.core.db import db
from fastapi import UploadFile, HTTPException
from typing import List, Optional
from app.modules.products.schemas import ProductCreate
from app.common.cloudinary import upload_image
from prisma.enums import ProductStatus

async def upload_product_images(files: List[UploadFile]):
    """
    Uploads multiple images to Cloudinary and returns their URLs.
    """
    if len(files) > 3:
        raise HTTPException(status_code=400, detail="Maximum 3 images allowed")
    
    image_urls = []
    for file in files:
        upload_result = await upload_image(file, folder="jorden/products")
        if upload_result:
            image_urls.append(upload_result.get("secure_url"))
            
    return {"urls": image_urls}

async def create_product(seller_id: int, data: ProductCreate):
    """
    Creates a new product using pre-uploaded image URLs.
    """
    # 1. Normalize Category Name
    category_name = data.category.upper().strip()
    
    # 2. Get or Create Category
    category = await db.category.upsert(
        where={"name": category_name},
        data={
            "create": {"name": category_name},
            "update": {}
        }
    )
            
    # 3. Create Product
    product = await db.product.create(
        data={
            "title": data.title,
            "description": data.description,
            "price": data.price,
            "condition": data.condition,
            "longitude": data.longitude,
            "latitude": data.latitude,
            "images": data.images,
            "sellerId": seller_id,
            "categoryId": category.id,
            "status": ProductStatus.ACTIVE
        },
        include={"category": True}
    )
    
    return product

async def get_seller_products(seller_id: int):
    """
    Returns all products belonging to a specific seller.
    """
    return await db.product.find_many(
        where={"sellerId": seller_id},
        include={"category": True},
        order={"createdAt": "desc"}
    )

async def get_all_products(category_filter: str = "ALL"):
    """
    Returns all ACTIVE products, optionally filtered by category.
    """
    query = {"status": ProductStatus.ACTIVE}
    
    if category_filter != "ALL":
        query["category"] = {"name": category_filter.upper().strip()}
        
    return await db.product.find_many(
        where=query,
        include={"category": True},
        order={"createdAt": "desc"}
    )

async def get_all_categories():
    """
    Returns all available categories.
    """
    return await db.category.find_many(order={"name": "asc"})
