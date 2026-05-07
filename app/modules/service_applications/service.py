from app.core.db import db
from fastapi import HTTPException
from typing import List
from app.modules.service_applications.schemas import ServiceApplicationCreate, ServiceApplicationStatusUpdate
from prisma.enums import ApplicationStatus, ServiceStatus

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
    return format_application_response(application)

async def get_service_applications(provider_id: int, service_id: int = None):
    """
    Returns applications for a provider's services.
    """
    where = {"service": {"providerId": provider_id}}
    if service_id:
        where["serviceId"] = service_id

    applications = await db.serviceapplication.find_many(
        where=where,
        include={"service": {"include": {"provider": {"include": {"profile": True}}}}, "client": {"include": {"profile": True}}, "tracking": True},
        order={"createdAt": "desc"}
    )
    return [format_application_response(a) for a in applications]

async def get_client_applications(client_id: int):
    """
    Returns applications sent by a client.
    """
    applications = await db.serviceapplication.find_many(
        where={"clientId": client_id},
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

    return format_application_response(updated_app)
