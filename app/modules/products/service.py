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

def format_product_response(product):
    """
    Helper to format product data, flattening profile images.
    """
    p_dict = product.model_dump()
    if product.seller:
        p_dict["seller"] = {
            "id": product.seller.id,
            "fullname": product.seller.fullname,
            "email": product.seller.email,
            "displayname": product.seller.displayname,
            "profile_image": product.seller.profile.profile_image if product.seller.profile else None
        }
    return p_dict

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
            
    # 3. Calculate total_fee
    tax = data.tax_fee or 0
    delivery = data.delivery_fee or 0
    total_fee = data.price + tax + delivery
            
    # 4. Create Product
    product = await db.product.create(
        data={
            "title": data.title,
            "description": data.description,
            "price": data.price,
            "tax_fee": tax,
            "delivery_fee": delivery,
            "total_fee": total_fee,
            "condition": data.condition,
            "longitude": data.longitude,
            "latitude": data.latitude,
            "images": data.images,
            "sellerId": seller_id,
            "categoryId": category.id,
            "status": ProductStatus.ACTIVE
        },
        include={"category": True, "seller": {"include": {"profile": True}}}
    )
    
    return format_product_response(product)

async def get_seller_products(seller_id: int, status_filter: str = "ALL"):
    """
    Returns all products belonging to a specific seller with status counts and optional filtering.
    """
    all_products = await db.product.find_many(
        where={"sellerId": seller_id},
        include={"category": True, "seller": {"include": {"profile": True}}},
        order={"createdAt": "desc"}
    )
    
    # Calculate counts from all products
    total_active = sum(1 for p in all_products if p.status == ProductStatus.ACTIVE)
    total_draft = sum(1 for p in all_products if p.status == ProductStatus.DRAFT)
    total_inactive = sum(1 for p in all_products if p.status == ProductStatus.INACTIVE)
    total_deleted = sum(1 for p in all_products if p.status == ProductStatus.DELETED)
    total_soldout = sum(1 for p in all_products if p.status == ProductStatus.SOLDOUT)
    
    # Apply filter to the list
    if status_filter != "ALL":
        filtered_products = [p for p in all_products if p.status == status_filter]
    else:
        filtered_products = all_products
    
    return {
        "total_products": len(all_products),
        "total_active": total_active,
        "total_draft": total_draft,
        "total_inactive": total_inactive,
        "total_deleted": total_deleted,
        "total_soldout": total_soldout,
        "products": [format_product_response(p) for p in filtered_products]
    }

async def get_all_products(category_filter: str = "ALL"):
    """
    Returns all ACTIVE products, optionally filtered by category.
    """
    query = {"status": ProductStatus.ACTIVE}
    
    if category_filter != "ALL":
        query["category"] = {"name": category_filter.upper().strip()}
        
    products = await db.product.find_many(
        where=query,
        include={"category": True, "seller": {"include": {"profile": True}}},
        order={"createdAt": "desc"}
    )
    
    return [format_product_response(p) for p in products]

async def get_all_categories():
    """
    Returns all available categories.
    """
    return await db.category.find_many(order={"name": "asc"})

async def delete_product(seller_id: int, product_id: int, hard_delete: bool = False):
    """
    Deletes a product.
    - Soft delete: Sets status to DELETED.
    - Hard delete: Removes from DB.
    Verifies that the product belongs to the seller.
    """
    product = await db.product.find_unique(where={"id": product_id})
    
    if not product or product.sellerId != seller_id:
        raise HTTPException(
            status_code=404, 
            detail="Product not found or access denied"
        )
    
    if hard_delete:
        await db.product.delete(where={"id": product_id})
        return {"message": "Product permanently deleted from database"}
    else:
        await db.product.update(
            where={"id": product_id},
            data={"status": ProductStatus.DELETED}
        )
        return {"message": "Product status updated to DELETED (soft delete)"}
