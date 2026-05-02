from fastapi import APIRouter, Depends, UploadFile, File
from typing import List
from app.modules.reviews import service, schemas
from app.modules.users.router import get_current_user_id

router = APIRouter(prefix="/reviews", tags=["Reviews"])

@router.post("/upload-images", response_model=schemas.ImageUploadResponse)
async def upload_images(
    files: List[UploadFile] = File(...),
    user_id: int = Depends(get_current_user_id)
):
    """
    Step 1: Upload images for a review. Returns list of Cloudinary URLs.
    """
    return await service.upload_review_images(files)

@router.post("/", response_model=schemas.ReviewResponse)
async def post_review(
    data: schemas.ReviewCreate,
    user_id: int = Depends(get_current_user_id)
):
    """
    Step 2: Post a review with comment, rating, and image URLs.
    Increments seller's trust score.
    """
    return await service.create_review(user_id, data)
