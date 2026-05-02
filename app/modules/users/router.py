from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.modules.users import service
from app.modules.users import service, schemas
from app.common.security import decode_token

router = APIRouter(prefix="/users", tags=["Users"])
security = HTTPBearer()

async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return int(payload.get("sub"))

@router.get("/profile", response_model=schemas.UserProfileResponse)
async def get_profile(user_id: int = Depends(get_current_user_id)):
    user = await service.get_user_profile(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

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
