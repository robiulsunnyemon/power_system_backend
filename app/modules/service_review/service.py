from app.core.db import db
from fastapi import HTTPException, status, UploadFile
from typing import List, Optional
from prisma.enums import ApplicationStatus

def format_review_response(review):
    """
    Helper to format review response and include client details correctly.
    """
    r_dict = review.model_dump()
    if review.client:
        r_dict["client"] = {
            "id": review.client.id,
            "fullname": review.client.fullname,
            "email": review.client.email,
            "displayname": review.client.displayname,
            "profile_image": review.client.profile.profile_image if review.client.profile else None
        }
    return r_dict

async def create_service_review(client_id: int, application_id: int, rating: int, comment: Optional[str] = None, image: Optional[UploadFile] = None):
    """
    Submits a review for a completed service application, uploads an optional single image to Cloudinary,
    and updates the provider's overall stats.
    """
    from app.common.cloudinary import upload_image

    # 1. Fetch the service application
    application = await db.serviceapplication.find_unique(
        where={"id": application_id},
        include={"service": True}
    )

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service application not found"
        )

    # 2. Check if application is completed
    if application.status != ApplicationStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reviews can only be submitted for completed service applications"
        )

    # 3. Check if the current user is the client who applied
    if application.clientId != client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to review this service application"
        )

    # 4. Check if a review already exists for this application
    existing_review = await db.servicereview.find_unique(
        where={"applicationId": application_id}
    )
    if existing_review:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already submitted a review for this service application"
        )

    provider_id = application.service.providerId

    # 5. Upload optional single image to Cloudinary
    uploaded_images = []
    if image and image.filename:
        upload_result = await upload_image(image, folder="jorden/service_reviews")
        if upload_result and "secure_url" in upload_result:
            uploaded_images.append(upload_result["secure_url"])

    # 6. Create the review
    review = await db.servicereview.create(
        data={
            "rating": rating,
            "comment": comment,
            "images": uploaded_images,
            "application": {"connect": {"id": application_id}},
            "client": {"connect": {"id": client_id}},
            "provider": {"connect": {"id": provider_id}}
        },
        include={
            "client": {"include": {"profile": True}}
        }
    )

    # 7. Update Provider Review Stats
    stats = await db.providerstats.find_unique(
        where={"providerId": provider_id}
    )

    if stats:
        new_total_reviews = stats.totalReviews + 1
        new_total_rating = stats.totalRating + rating
        new_average_rating = round(new_total_rating / new_total_reviews, 2)

        await db.providerstats.update(
            where={"providerId": provider_id},
            data={
                "totalRating": new_total_rating,
                "totalReviews": new_total_reviews,
                "averageRating": new_average_rating
            }
        )
    else:
        await db.providerstats.create(
            data={
                "providerId": provider_id,
                "totalRating": rating,
                "averageRating": float(rating),
                "totalReviews": 1
            }
        )

    return format_review_response(review)

async def get_provider_reviews(provider_id: int):
    """
    Returns all reviews received by a service provider.
    """
    reviews = await db.servicereview.find_many(
        where={"providerId": provider_id},
        include={
            "client": {"include": {"profile": True}}
        },
        order={"createdAt": "desc"}
    )
    return [format_review_response(r) for r in reviews]

async def get_provider_stats(provider_id: int):
    """
    Returns rating stats for a service provider.
    """
    stats = await db.providerstats.find_unique(
        where={"providerId": provider_id}
    )

    if not stats:
        # Return default empty stats if none exist
        return {
            "providerId": provider_id,
            "totalRating": 0,
            "averageRating": 0.0,
            "totalReviews": 0
        }

    return stats
