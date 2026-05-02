from app.core.db import db
from app.modules.users.schemas import UpdateProfileRequest
from app.common.cloudinary import upload_image, delete_image, get_public_id_from_url
from fastapi import UploadFile, HTTPException

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
