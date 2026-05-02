from app.core.db import db
from fastapi import HTTPException, UploadFile
from typing import List
from app.modules.reviews.schemas import ReviewCreate
from app.common.utils import calculate_trust_score
from prisma.enums import OrderStatus
from app.common.cloudinary import upload_image

async def upload_review_images(files: List[UploadFile]):
    """
    Uploads multiple images to Cloudinary and returns their URLs.
    """
    urls = []
    for file in files:
        result = await upload_image(file, folder="jorden/reviews")
        if result:
            urls.append(result.get("secure_url"))
    return {"urls": urls}

async def create_review(buyer_id: int, data: ReviewCreate):
    """
    Creates a review with optional images and updates the seller's trust score.
    Logic: raw_score += rating * 20
    """
    # 1. Check if order exists and belongs to the buyer
    order = await db.order.find_unique(
        where={"id": data.order_id},
        include={"product": True, "review": True}
    )
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.userId != buyer_id:
        raise HTTPException(status_code=403, detail="You can only review your own orders")
        
    # 2. Check if order is DELIVERED
    if order.status != OrderStatus.DELIVERED:
        raise HTTPException(status_code=400, detail="You can only review delivered orders")
        
    # 3. Check if already reviewed
    if order.review:
        raise HTTPException(status_code=400, detail="This order has already been reviewed")
        
    # 4. Create Review
    review = await db.review.create(
        data={
            "rating": data.rating,
            "comment": data.comment,
            "images": data.images,
            "buyerId": buyer_id,
            "sellerId": order.product.sellerId,
            "productId": order.productId,
            "orderId": data.order_id
        }
    )
    
    # 5. Update Seller Trust Score
    profile = await db.userprofile.find_unique(where={"userId": order.product.sellerId})
    current_raw = profile.raw_score if profile else 0
    
    points = data.rating * 20
    new_raw = current_raw + points
    new_trust = calculate_trust_score(new_raw)
    
    await db.userprofile.upsert(
        where={"userId": order.product.sellerId},
        data={
            "create": {
                "userId": order.product.sellerId,
                "raw_score": new_raw,
                "trust_score": new_trust
            },
            "update": {
                "raw_score": new_raw,
                "trust_score": new_trust
            }
        }
    )
        
    return review
