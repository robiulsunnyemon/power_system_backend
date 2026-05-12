from app.core.db import db
from fastapi import HTTPException
from typing import List, Optional
from app.modules.services.schemas import ServiceCreate, ServiceUpdate
from prisma.enums import ServiceStatus
from prisma.types import ServiceUpdateInput
from prisma import Json
import json

def format_service_response(service):
    """
    Helper to format service data, flattening profile images.
    """
    s_dict = service.model_dump()
    if service.provider:
        s_dict["provider"] = {
            "id": service.provider.id,
            "fullname": service.provider.fullname,
            "email": service.provider.email,
            "displayname": service.provider.displayname,
            "profile_image": service.provider.profile.profile_image if service.provider.profile else None
        }
    return s_dict

async def create_service(provider_id: int, data: ServiceCreate):
    """
    Creates a new service post.
    """
    # 1. Normalize Category Name
    category_name = data.category.strip() if data.category else None
    
    # 3. Format requirements
    req_data = [r.model_dump() for r in data.requirements] if data.requirements else []
    avail_data = data.availability if data.availability else []
            
    # 4. Create Service
    service = await db.service.create(
        data={
            "title": data.title,
            "description": data.description,
            "price": data.price,
            "pricingType": data.pricingType,
            "longitude": data.longitude,
            "latitude": data.latitude,
            "requirements": Json(req_data),
            "availability": Json(avail_data),
            "images": data.images,
            "provider": {"connect": {"id": provider_id}},
            "category": category_name,
            "status": data.status
        },
        include={"provider": {"include": {"profile": True}}}
    )
    
    # Notify Past Clients (who had COMPLETED applications with this provider)
    from prisma.enums import ApplicationStatus
    past_clients = await db.serviceapplication.find_many(
        where={
            "service": {"providerId": provider_id},
            "status": ApplicationStatus.COMPLETED
        },
        distinct=["clientId"]
    )
    
    from app.modules.notifications.service import send_notification
    for client in past_clients:
        await send_notification(
            user_id=client.clientId,
            title="New Service from your Provider",
            description=f"Your previous service provider has created a new service: '{service.title}'",
            notification_type="new_service",
            image=service.images[0] if service.images else None
        )
    
    return format_service_response(service)

async def get_provider_services(provider_id: int, status_filter: str = "ALL"):
    """
    Returns all services belonging to a specific provider.
    """
    all_services = await db.service.find_many(
        where={"providerId": provider_id},
        include={"provider": {"include": {"profile": True}}},
        order={"createdAt": "desc"}
    )
    
    total_active = sum(1 for s in all_services if s.status == ServiceStatus.PUBLISHED)
    total_draft = sum(1 for s in all_services if s.status == ServiceStatus.DRAFT)
    
    if status_filter != "ALL":
        filtered_services = [s for s in all_services if s.status == status_filter]
    else:
        filtered_services = all_services
        
    return {
        "total_services": len(all_services),
        "total_active": total_active,
        "total_draft": total_draft,
        "services": [format_service_response(s) for s in filtered_services]
    }

async def get_all_services(
    category_filter: str = "ALL",
    page: int = 1,
    page_size: int = 10
):
    """
    Returns all PUBLISHED services, optionally filtered by category, with pagination.
    """
    query = {"status": ServiceStatus.PUBLISHED}
    
    if category_filter != "ALL":
        query["category"] = category_filter.strip()
        
    # Get total count for pagination
    total_count = await db.service.count(where=query)
    
    # Calculate skip
    skip = (page - 1) * page_size
    
    services = await db.service.find_many(
        where=query,
        include={"provider": {"include": {"profile": True}}},
        order={"createdAt": "desc"},
        skip=skip,
        take=page_size
    )
    
    return {
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "services": [format_service_response(s) for s in services]
    }

async def get_service_by_id(service_id: int):
    """
    Returns a single service by ID (public endpoint).
    """
    service = await db.service.find_unique(
        where={"id": service_id},
        include={"provider": {"include": {"profile": True}}}
    )
    
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
        
    return format_service_response(service)

async def update_service(provider_id: int, service_id: int, data: ServiceUpdate):
    """
    Updates an existing service.
    """
    service = await db.service.find_unique(where={"id": service_id})
    
    if not service or service.providerId != provider_id:
        raise HTTPException(status_code=404, detail="Service not found or access denied")
        
    update_data = data.model_dump(exclude_unset=True)
    
    if "category" in update_data:
        update_data["category"] = update_data["category"].strip() if update_data["category"] else None
        
    if "requirements" in update_data and update_data["requirements"]:
        update_data["requirements"] = Json([r for r in update_data["requirements"]])
        
    if "availability" in update_data and update_data["availability"]:
        update_data["availability"] = Json(update_data["availability"])

    updated_service = await db.service.update(
        where={"id": service_id},
        data=update_data, # type: ignore
        include={"provider": {"include": {"profile": True}}}
    )
    
    return format_service_response(updated_service)

async def delete_service(provider_id: int, service_id: int):
    """
    Soft deletes a service by setting status to CLOSED/DELETED (Wait, ServiceStatus doesn't have DELETED, maybe CLOSED).
    """
    service = await db.service.find_unique(where={"id": service_id})
    
    if not service or service.providerId != provider_id:
        raise HTTPException(status_code=404, detail="Service not found or access denied")
        
    await db.service.update(
        where={"id": service_id},
        data={"status": ServiceStatus.CLOSED}
    )
    return {"message": "Service closed successfully"}
