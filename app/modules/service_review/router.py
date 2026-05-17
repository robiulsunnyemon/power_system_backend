from fastapi import APIRouter, Depends, Path, status, Form, File, UploadFile
from typing import List, Optional
from app.modules.service_review.schemas import (
    ServiceReviewResponse, ProviderStatsResponse
)
from app.modules.service_review.service import (
    create_service_review, get_provider_reviews, get_provider_stats
)
from app.modules.users.router import get_current_user_id

router = APIRouter(prefix="/service-reviews", tags=["Service Reviews"])

@router.post("/{application_id}", response_model=ServiceReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review_endpoint(
    rating: int = Form(..., ge=1, le=5, description="Rating must be between 1 and 5"),
    comment: Optional[str] = Form(None, description="Optional comment/review for the provider"),
    image: Optional[UploadFile] = File(None, description="Optional single image file to upload"),
    application_id: int = Path(..., title="ID of the completed service application to review"),
    client_id: int = Depends(get_current_user_id)
):
    """
    Submit a review and rating for a completed service application, with an optional single image file upload.
    """
    return await create_service_review(
        client_id=client_id,
        application_id=application_id,
        rating=rating,
        comment=comment,
        image=image
    )

@router.get("/provider/{provider_id}", response_model=List[ServiceReviewResponse])
async def get_provider_reviews_endpoint(
    provider_id: int = Path(..., title="ID of the service provider")
):
    """
    Retrieve all reviews received by a specific service provider.
    """
    return await get_provider_reviews(provider_id)

@router.get("/provider/{provider_id}/stats", response_model=ProviderStatsResponse)
async def get_provider_stats_endpoint(
    provider_id: int = Path(..., title="ID of the service provider")
):
    """
    Retrieve total rating, average rating, and total reviews count for a specific service provider.
    """
    return await get_provider_stats(provider_id)
