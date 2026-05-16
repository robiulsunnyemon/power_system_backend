from app.core.db import db
from app.modules.users.schemas import UpdateProfileRequest, DeleteAccountRequest
from app.common.cloudinary import upload_image, delete_image, get_public_id_from_url
from app.common.security import verify_password
from fastapi import UploadFile, HTTPException
from app.modules.products.service import format_product_response
from prisma.enums import ProductStatus
from app.core.websocket import manager

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
    
    if not seller or "SELLER" not in seller.roles:
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
        "positive": round(positive_pct, 1),
        "is_online": manager.is_user_online(seller.id)
    }
    
    # 4. Format Products
    active_products = [format_product_response(p) for p in seller.products]
    
    # 5. Format Reviews
    reviews = []
    for r in seller.reviews_received:
        # Get reviewer name (prefer displayname, fallback to fullname)
        reviewer_name = r.buyer.displayname if r.buyer.displayname else r.buyer.fullname
        
        # Get reviewer role (primary role)
        reviewer_role = r.buyer.roles[0] if r.buyer.roles else "USER"
        
        # Get reviewer image
        reviewer_image = r.buyer.profile.profile_image if r.buyer.profile else None

        reviews.append({
            "id": r.id,
            "rating": r.rating,
            "comment": r.comment,
            "createdAt": r.createdAt,
            "buyerId": r.buyerId,
            "sellerId": r.sellerId,
            "productId": r.productId,
            "orderId": r.orderId,
            "reviewer_name": reviewer_name,
            "reviewer_role": reviewer_role,
            "reviewer_image": reviewer_image
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
    user_dict["trust_score"] = user.profile.trust_score if user.profile else 0
    user_dict["raw_score"] = user.profile.raw_score if user.profile else 0
    user_dict["is_online"] = manager.is_user_online(user_id)
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
    user_dict["trust_score"] = user.profile.trust_score if user.profile else 0
    user_dict["raw_score"] = user.profile.raw_score if user.profile else 0
    user_dict["is_online"] = manager.is_user_online(user_id)
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

async def become_seller(user_id: int):
    user = await db.user.find_unique(where={"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    updated_roles = user.roles
    message = "Already a SELLER. Returning a new token."
    
    if "SELLER" not in user.roles:
        updated_roles = user.roles + ["SELLER"]
        message = "Successfully upgraded to SELLER"
        
    # Always increment tokenVersion to invalidate old tokens
    new_token_version = user.tokenVersion + 1
    
    await db.user.update(
        where={"id": user_id},
        data={
            "roles": {"set": updated_roles},
            "tokenVersion": new_token_version,
            "lastActiveRole": "SELLER"
        }
    )
    
    from app.common.security import create_access_token
    new_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "roles": updated_roles, "token_version": new_token_version, "last_active_role": "SELLER"}
    )
    
    return {
        "message": message,
        "access_token": new_token,
        "token_type": "bearer",
        "last_active_role": "SELLER"
    }

async def become_service_provider(user_id: int):
    user = await db.user.find_unique(where={"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    updated_roles = user.roles
    message = "Already a SERVICE_PROVIDER. Returning a new token."
    
    if "SERVICE_PROVIDER" not in user.roles:
        updated_roles = user.roles + ["SERVICE_PROVIDER"]
        message = "Successfully upgraded to SERVICE_PROVIDER"
        
    # Always increment tokenVersion to invalidate old tokens
    new_token_version = user.tokenVersion + 1
    
    await db.user.update(
        where={"id": user_id},
        data={
            "roles": {"set": updated_roles},
            "tokenVersion": new_token_version,
            "lastActiveRole": "SERVICE_PROVIDER"
        }
    )
    
    from app.common.security import create_access_token
    new_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "roles": updated_roles, "token_version": new_token_version, "last_active_role": "SERVICE_PROVIDER"}
    )
    
    return {
        "message": message,
        "access_token": new_token,
        "token_type": "bearer",
        "last_active_role": "SERVICE_PROVIDER"
    }

async def become_user(user_id: int):
    """
    Endpoint for a user to ensure they have the base USER role and get a fresh token.
    """
    user = await db.user.find_unique(where={"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    updated_roles = user.roles
    message = "Already a USER. Returning a new token."
    
    if "USER" not in user.roles:
        updated_roles = user.roles + ["USER"]
        message = "Successfully added USER role"
        
    # Always increment tokenVersion to invalidate old tokens
    new_token_version = user.tokenVersion + 1
    
    await db.user.update(
        where={"id": user_id},
        data={
            "roles": {"set": updated_roles},
            "tokenVersion": new_token_version,
            "lastActiveRole": "USER"
        }
    )
    
    from app.common.security import create_access_token
    new_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "roles": updated_roles, "token_version": new_token_version, "last_active_role": "USER"}
    )
    
    return {
        "message": message,
        "access_token": new_token,
        "token_type": "bearer",
        "last_active_role": "USER"
    }

async def delete_my_account(user_id: int, data: DeleteAccountRequest):
    user = await db.user.find_unique(where={"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if not verify_password(data.password, user.password):
        raise HTTPException(status_code=400, detail="Incorrect password")
        
    await db.user.update(
        where={"id": user_id},
        data={
            "accountStatus": "DELETE",
            "tokenVersion": user.tokenVersion + 1
        }
    )
    return {"message": "Account deleted successfully. You have been logged out."}

async def get_user_summary(user_id: int):
    """
    Returns a summary of user's activity: total listings, completed jobs, and trust score.
    """
    from prisma.enums import OrderStatus, ApplicationStatus
    
    # 1. Listings Count
    listings_count = await db.product.count(where={"sellerId": user_id})
    
    # 2. Jobs Completed Count (Orders + Service Applications)
    delivered_orders = await db.order.count(
        where={
            "product": {"sellerId": user_id},
            "status": OrderStatus.DELIVERED
        }
    )
    
    completed_services = await db.serviceapplication.count(
        where={
            "service": {"providerId": user_id},
            "status": ApplicationStatus.COMPLETED
        }
    )
    
    total_jobs = delivered_orders + completed_services
    
    # 3. Total Reviews Received
    total_reviews = await db.review.count(where={"sellerId": user_id})
    
    # 4. Trust Score
    profile = await db.userprofile.find_unique(where={"userId": user_id})
    trust_score = profile.trust_score if profile else 0.0
    
    return {
        "listings": listings_count,
        "jobs_completed": total_jobs,
        "total_order_delivery": delivered_orders,
        "total_review": total_reviews,
        "trust_score": trust_score
    }


