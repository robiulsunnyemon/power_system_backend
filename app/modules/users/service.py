from app.core.db import db
from app.modules.users.schemas import UpdateProfileRequest
from app.common.cloudinary import upload_image, delete_image, get_public_id_from_url
from fastapi import UploadFile, HTTPException
from app.modules.products.service import format_product_response
from prisma.enums import ProductStatus

async def get_seller_public_profile(seller_id: int):
    """
    Fetches public profile of a seller including active products, reviews, and stats.
    """
    # 1. Fetch Seller with Profile, Active Products, and Received Reviews
    seller = await db.user.find_unique(
        where={"id": seller_id},
        include={
            "profile": True,
            "products": {
                "where": {"status": ProductStatus.ACTIVE},
                "include": {"category": True, "seller": {"include": {"profile": True}}}
            },
            "reviews_received": {
                "include": {"buyer": {"include": {"profile": True}}}
            }
        }
    )
    
    if not seller or seller.role != "SELLER":
        raise HTTPException(status_code=404, detail="Seller not found")
        
    # 2. Calculate Stats
    raw_score = seller.profile.raw_score if seller.profile else 0
    trust_score = seller.profile.trust_score if seller.profile else 0
    
    # Badge Logic
    if raw_score >= 800:
        badge = "Elite"
    elif raw_score >= 500:
        badge = "Verified"
    elif raw_score >= 300:
        badge = "Trusted"
    else:
        badge = "New Member"
        
    # Delivery Count
    from prisma.enums import OrderStatus
    total_delivery = await db.order.count(
        where={
            "product": {"sellerId": seller_id},
            "status": OrderStatus.DELIVERED
        }
    )
    
    # Rating Stats
    ratings = [r.rating for r in seller.reviews_received]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0.0
    
    # Positive Percentage (Based on Average Rating)
    # (avg_rating / 5) * 100 -> Premium logic
    positive_pct = (avg_rating / 5) * 100 if ratings else 0.0
    
    # 3. Format Seller Info
    seller_info = {
        "id": seller.id,
        "fullname": seller.fullname,
        "displayname": seller.displayname,
        "profile_image": seller.profile.profile_image if seller.profile else None,
        "raw_score": raw_score,
        "trust_score": trust_score,
        "badge": badge,
        "total_delivery": total_delivery,
        "average_rating": round(avg_rating, 1),
        "positive": round(positive_pct, 1)
    }
    
    # 4. Format Products
    active_products = [format_product_response(p) for p in seller.products]
    
    # 5. Format Reviews
    reviews = []
    for r in seller.reviews_received:
        reviews.append({
            "id": r.id,
            "rating": r.rating,
            "comment": r.comment,
            "createdAt": r.createdAt,
            "buyerId": r.buyerId,
            "sellerId": r.sellerId,
            "productId": r.productId,
            "orderId": r.orderId
        })
        
    return {
        "seller": seller_info,
        "active_products": active_products,
        "reviews": reviews
    }

async def get_user_profile(user_id: int):
    user = await db.user.find_unique(
        where={"id": user_id},
        include={"profile": True}
    )
    if not user:
        return None
    
    user_dict = user.model_dump()
    user_dict["profile_image"] = user.profile.profile_image if user.profile else None
    return user_dict

async def update_user_profile(user_id: int, data: UpdateProfileRequest):
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    user = await db.user.update(
        where={"id": user_id},
        data=update_data,
        include={"profile": True}
    )
    
    user_dict = user.model_dump()
    user_dict["profile_image"] = user.profile.profile_image if user.profile else None
    return user_dict

async def update_profile_image(user_id: int, file: UploadFile):
    # Get current profile to check for existing image
    profile = await db.userprofile.find_unique(where={"userId": user_id})
    
    # Upload new image to Cloudinary
    upload_result = await upload_image(file)
    if not upload_result:
        raise HTTPException(status_code=500, detail="Failed to upload image to Cloudinary")
    
    new_image_url = upload_result.get("secure_url")
    
    # If old image exists, delete it from Cloudinary
    if profile and profile.profile_image:
        old_public_id = get_public_id_from_url(profile.profile_image)
        if old_public_id:
            delete_image(old_public_id)
            
    # Update or create UserProfile in DB
    await db.userprofile.upsert(
        where={"userId": user_id},
        data={
            "create": {"userId": user_id, "profile_image": new_image_url},
            "update": {"profile_image": new_image_url}
        }
    )
    
    return await get_user_profile(user_id)

async def delete_profile_image(user_id: int):
    profile = await db.userprofile.find_unique(where={"userId": user_id})
    if not profile or not profile.profile_image:
        raise HTTPException(status_code=404, detail="No profile image found")
    
    # Delete from Cloudinary
    public_id = get_public_id_from_url(profile.profile_image)
    if public_id:
        delete_image(public_id)
        
    # Update DB
    await db.userprofile.update(
        where={"userId": user_id},
        data={"profile_image": None}
    )
    
    return await get_user_profile(user_id)
