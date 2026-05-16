from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.modules.users import service, schemas
from app.common.security import decode_token
from app.core.db import db

router = APIRouter(prefix="/users", tags=["Users"])
security = HTTPBearer()

async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
    user_id = int(payload.get("sub"))
    token_version = payload.get("token_version")
    
    user = await db.user.find_unique(where={"id": user_id})
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        
    if user.tokenVersion != token_version:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been invalidated. Please login again.")
        
    return user_id

@router.get("/profile", response_model=schemas.UserProfileResponse)
async def get_profile(user_id: int = Depends(get_current_user_id)):
    user = await service.get_user_profile(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.get("/seller/me", response_model=schemas.SellerPublicProfileResponse)
async def get_my_seller_profile(user_id: int = Depends(get_current_user_id)):
    """
    Endpoint for a logged-in seller to see their own public profile data.
    """
    return await service.get_seller_public_profile(user_id)

@router.get("/seller/{seller_id}", response_model=schemas.SellerPublicProfileResponse)
async def get_seller_profile(seller_id: int):
    """
    Public endpoint to get a seller's profile, products, and reviews.
    """
    return await service.get_seller_public_profile(seller_id)

@router.put("/profile", response_model=schemas.UserProfileResponse)
async def update_profile(data: schemas.UpdateProfileRequest, user_id: int = Depends(get_current_user_id)):
    return await service.update_user_profile(user_id, data)

@router.post("/profile/image", response_model=schemas.UserProfileResponse)
async def upload_profile_image(file: UploadFile = File(...), user_id: int = Depends(get_current_user_id)):
    return await service.update_profile_image(user_id, file)

@router.delete("/profile/image", response_model=schemas.UserProfileResponse)
async def delete_profile_image(user_id: int = Depends(get_current_user_id)):
    return await service.delete_profile_image(user_id)

@router.post("/become-seller")
async def become_seller(user_id: int = Depends(get_current_user_id)):
    """
    Endpoint for a regular user to upgrade to a SELLER role.
    """
    return await service.become_seller(user_id)

@router.post("/become-service-provider")
async def become_service_provider(user_id: int = Depends(get_current_user_id)):
    """
    Endpoint for a regular user to upgrade to a SERVICE_PROVIDER role.
    """
    return await service.become_service_provider(user_id)

@router.post("/become-user")
async def become_user(user_id: int = Depends(get_current_user_id)):
    """
    Endpoint for a user to ensure they have the base USER role and get a fresh token.
    """
    return await service.become_user(user_id)

@router.delete("/delete-account")
async def delete_account(data: schemas.DeleteAccountRequest, user_id: int = Depends(get_current_user_id)):
    """
    Endpoint for a user to delete their own account.
    """
    return await service.delete_my_account(user_id, data)

@router.get("/summary", response_model=schemas.UserSummaryResponse)
async def get_user_summary(user_id: int = Depends(get_current_user_id)):
    """
    Endpoint to get a summary of user's activity (listings, jobs, trust score).
    """
    return await service.get_user_summary(user_id)

