from app.core.db import db
from fastapi import HTTPException
from typing import List,Optional
from app.modules.service_applications.schemas import ServiceApplicationCreate, ServiceApplicationStatusUpdate
from prisma.enums import ApplicationStatus, ServiceStatus
from datetime import datetime, timedelta, timezone
from app.modules.notifications.service import send_notification

def format_application_response(app):
    """
    Helper to format application data.
    """
    a_dict = app.model_dump()
    if app.client:
        a_dict["client"] = {
            "id": app.client.id,
            "fullname": app.client.fullname,
            "email": app.client.email,
            "displayname": app.client.displayname,
            "profile_image": app.client.profile.profile_image if app.client.profile else None
        }
    if app.service and app.service.provider:
        raw_score = app.service.provider.profile.raw_score if app.service.provider.profile else 0
        trust_score = app.service.provider.profile.trust_score if app.service.provider.profile else 0
        
        if raw_score >= 800:
            badge = "Elite"
        elif raw_score >= 500:
            badge = "Verified"
        elif raw_score >= 300:
            badge = "Trusted"
        else:
            badge = "New Member"

        a_dict["service"]["provider"] = {
            "id": app.service.provider.id,
            "fullname": app.service.provider.fullname,
            "email": app.service.provider.email,
            "displayname": app.service.provider.displayname,
            "profile_image": app.service.provider.profile.profile_image if app.service.provider.profile else None,
            "trust_score": trust_score,
            "badge": badge
        }
    return a_dict

async def apply_for_service(client_id: int, service_id: int, data: ServiceApplicationCreate):
    """
    Creates a new application for a service.
    """
    # Verify service exists
    service = await db.service.find_unique(where={"id": service_id})
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    # Check if already applied
    existing = await db.serviceapplication.find_first(
        where={"clientId": client_id, "serviceId": service_id}
    )
    if existing:
        raise HTTPException(status_code=400, detail="You have already applied for this service")

    application = await db.serviceapplication.create(
        data={
            "proposedRate": data.proposedRate,
            "expectedStartDate": data.expectedStartDate,
            "coverLetter": data.coverLetter,
            "client": {"connect": {"id": client_id}},
            "service": {"connect": {"id": service_id}},
            "tracking": {
                "create": [
                    {"status": "PENDING"},
                    {"status": "UNDER_REVIEW"}
                ]
            }
        },
        include={"service": {"include": {"provider": {"include": {"profile": True}}}}, "client": {"include": {"profile": True}}, "tracking": True}
    )

    # Notify Provider
    provider_id = application.service.providerId
    await send_notification(
        user_id=provider_id,
        title="New Service Application",
        description=f"You have a new application for '{application.service.title}'.",
        notification_type="service",
        image=application.service.images[0] if application.service.images else None
    )

    return format_application_response(application)

async def get_service_applications(provider_id: int, service_id: int = None, status: Optional[ApplicationStatus] = None):
    """
    Returns applications and status counts for a provider's services.
    If status is None, returns all applications regardless of status.
    """
    import asyncio

    base_where = {
        "service": {"providerId": provider_id}
    }
    if service_id:
        base_where["serviceId"] = service_id

    # Filtered applications: apply status filter only if a specific status is provided
    where = {**base_where}
    if status is not None:
        where["status"] = status

    applications = await db.serviceapplication.find_many(
        where=where,
        include={"service": {"include": {"provider": {"include": {"profile": True}}}}, "client": {"include": {"profile": True}}, "tracking": True},
        order={"createdAt": "desc"}
    )

    # Calculate status counts in parallel
    pending_task = db.serviceapplication.count(where={**base_where, "status": ApplicationStatus.PENDING})
    accepted_task = db.serviceapplication.count(where={**base_where, "status": ApplicationStatus.ACCEPTED})
    declined_task = db.serviceapplication.count(where={**base_where, "status": ApplicationStatus.DECLINED})
    completed_task = db.serviceapplication.count(where={**base_where, "status": ApplicationStatus.COMPLETED})

    pending_count, accepted_count, declined_count, completed_count = await asyncio.gather(
        pending_task, accepted_task, declined_task, completed_task
    )

    return {
        "pending_count": pending_count,
        "accepted_count": accepted_count,
        "declined_count": declined_count,
        "completed_count": completed_count,
        "requests": [format_application_response(a) for a in applications]
    }

async def get_client_applications(client_id: int, application_id: Optional[int] = None, status: str = "ALL"):
    """
    Returns applications sent by a client, optionally filtered by application ID and status.
    """
    where = {"clientId": client_id}
    if application_id:
        where["id"] = application_id
    
    if status != "ALL":
        where["status"] = status

    applications = await db.serviceapplication.find_many(
        where=where,
        include={"service": {"include": {"provider": {"include": {"profile": True}}}}, "client": {"include": {"profile": True}}, "tracking": True},
        order={"createdAt": "desc"}
    )
    return [format_application_response(a) for a in applications]

async def update_application_status(provider_id: int, application_id: int, data: ServiceApplicationStatusUpdate):
    """
    Updates application status (Accept/Decline).
    If accepted, creates a ServiceOrder.
    """
    application = await db.serviceapplication.find_unique(
        where={"id": application_id},
        include={"service": {"include": {"provider": True}}}
    )
    
    if not application or application.service.providerId != provider_id:
        raise HTTPException(status_code=404, detail="Application not found or access denied")

    if data.status == ApplicationStatus.ACCEPTED or str(data.status) == "ACCEPTED":
        # Find other pending applications to decline and add tracking
        other_apps = await db.serviceapplication.find_many(
            where={
                "serviceId": application.serviceId,
                "status": ApplicationStatus.PENDING
            }
        )
        
        for other_app in other_apps:
            if other_app.id != application_id:
                await db.serviceapplication.update(
                    where={"id": other_app.id},
                    data={
                        "status": ApplicationStatus.DECLINED,
                        "tracking": {
                            "create": {"status": "DECLINED"}
                        }
                    }
                )
            
        # Update service status to CLOSED
        await db.service.update(
            where={"id": application.serviceId},
            data={"status": ServiceStatus.CLOSED}
        )

    # Determine status string for tracking
    status_str = data.status.name if hasattr(data.status, "name") else str(data.status)
    if isinstance(data.status, str) and "." in data.status:
        status_str = data.status.split(".")[-1] # handle ApplicationStatus.ACCEPTED as string

    updated_app = await db.serviceapplication.update(
        where={"id": application_id},
        data={
            "status": data.status,
            "tracking": {
                "create": {"status": status_str}
            }
        },
        include={"service": {"include": {"provider": {"include": {"profile": True}}}}, "client": {"include": {"profile": True}}, "tracking": True}
    )

    # Notify Client
    status_msg_map = {
        ApplicationStatus.ACCEPTED: "Your service application has been accepted.",
        ApplicationStatus.COMPLETED: "Your service has been marked as completed.",
        ApplicationStatus.DECLINED: "Your service application has been declined."
    }
    
    if data.status in status_msg_map:
        await send_notification(
            user_id=updated_app.clientId,
            title=f"Application Update: {data.status}",
            description=status_msg_map[data.status],
            notification_type="service",
            image=updated_app.service.images[0] if updated_app.service.images else None
        )

    return format_application_response(updated_app)

async def get_provider_earnings(provider_id: int):
    """
    Returns earnings statistics and history for a service provider.
    """
    now = datetime.now(timezone.utc)
    
    # Fetch all applications for the provider's services
    applications = await db.serviceapplication.find_many(
        where={
            "service": {"providerId": provider_id}
        },
        include={"service": True},
        order={"updatedAt": "desc"}
    )

    total_completed_jobs = sum(1 for a in applications if str(a.status).endswith("COMPLETED"))
    total_earnings = sum(a.proposedRate for a in applications if str(a.status).endswith("COMPLETED"))
    
    # Pending earnings are from ACCEPTED but not yet COMPLETED applications
    pending_earnings = sum(a.proposedRate for a in applications if str(a.status).endswith("ACCEPTED"))

    # Time-based quick stats (based on updatedAt for completed status)
    start_of_week = now - timedelta(days=now.weekday())
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
    
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    earnings_this_week = sum(
        a.proposedRate for a in applications 
        if str(a.status).endswith("COMPLETED") and a.updatedAt >= start_of_week
    )
    earnings_this_month = sum(
        a.proposedRate for a in applications 
        if str(a.status).endswith("COMPLETED") and a.updatedAt >= start_of_month
    )

    # History (Recent 15 items)
    history = []
    for a in applications[:15]:
        history.append({
            "id": a.id,
            "title": a.service.title,
            "amount": a.proposedRate,
            "status": a.status,
            "date": a.updatedAt,
            "images": a.service.images
        })

    return {
        "total_earnings": total_earnings,
        "pending_earnings": pending_earnings,
        "quick_stats": {
            "this_week": earnings_this_week,
            "this_month": earnings_this_month,
            "total_completed_jobs": total_completed_jobs
        },
        "history": history
    }


async def get_user_earnings(user_id: int):
    """
    Returns earnings statistics and history for a service provider.
    """
    now = datetime.now(timezone.utc)

    # Fetch all applications where the user was the applicant (worker/client)
    applications = await db.serviceapplication.find_many(
        where={
            "clientId": user_id
        },
        include={"service": True},
        order={"updatedAt": "desc"}
    )

    total_completed_jobs = sum(1 for a in applications if str(a.status).endswith("COMPLETED"))
    total_earnings = sum(a.proposedRate for a in applications if str(a.status).endswith("COMPLETED"))

    # Pending earnings are from ACCEPTED but not yet COMPLETED applications
    pending_earnings = sum(a.proposedRate for a in applications if str(a.status).endswith("ACCEPTED"))

    # Time-based quick stats (based on updatedAt for completed status)
    start_of_week = now - timedelta(days=now.weekday())
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)

    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    earnings_this_week = sum(
        a.proposedRate for a in applications
        if str(a.status).endswith("COMPLETED") and a.updatedAt >= start_of_week
    )
    earnings_this_month = sum(
        a.proposedRate for a in applications
        if str(a.status).endswith("COMPLETED") and a.updatedAt >= start_of_month
    )

    # History (Recent 15 items)
    history = []
    for a in applications[:15]:
        history.append({
            "id": a.id,
            "title": a.service.title,
            "amount": a.proposedRate,
            "status": a.status,
            "date": a.updatedAt,
            "images": a.service.images
        })

    return {
        "total_earnings": total_earnings,
        "pending_earnings": pending_earnings,
        "quick_stats": {
            "this_week": earnings_this_week,
            "this_month": earnings_this_month,
            "total_completed_jobs": total_completed_jobs
        },
        "history": history
    }
