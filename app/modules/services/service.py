from app.core.db import db
from fastapi import HTTPException, UploadFile
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from app.common.cloudinary import upload_image
from app.modules.services.schemas import ServiceCreate, ServiceUpdate
from app.modules.settings.service import get_service_charges
from app.modules.payments.service import (
    get_or_create_stripe_customer,
    create_ephemeral_key,
    create_payment_intent,
    get_stripe_api_key
)
from prisma.enums import ServiceStatus, PaymentStatus
from prisma.types import ServiceUpdateInput
from prisma import Json
import json

async def upload_service_images(files: List[UploadFile]):
    """
    Uploads multiple images to Cloudinary and returns their URLs.
    """
    if len(files) > 3:
        raise HTTPException(status_code=400, detail="Maximum 3 images allowed")
    
    image_urls = []
    for file in files:
        upload_result = await upload_image(file, folder="jorden/services")
        if upload_result:
            image_urls.append(upload_result.get("secure_url"))
            
    return {"urls": image_urls}

def format_service_response(service):
    """
    Helper to format service data, flattening profile images.
    """
    s_dict = service.model_dump()
    if hasattr(service, "provider") and service.provider:
        s_dict["provider"] = {
            "id": service.provider.id,
            "fullname": service.provider.fullname,
            "email": service.provider.email,
            "displayname": service.provider.displayname,
            "profile_image": service.provider.profile.profile_image if hasattr(service.provider, "profile") and service.provider.profile else None
        }
    return s_dict

async def create_service(provider_id: int, data: ServiceCreate):
    """
    Creates a new service post with upfront platform and optional priority fees.
    Initially creates as DRAFT and PENDING payment until confirmed via Stripe.
    """
    # 1. Normalize Category Name
    category_name = data.category.strip() if data.category else None
    
    # 2. Format requirements & availability
    req_data = [r.model_dump() for r in data.requirements] if data.requirements else []
    avail_data = data.availability if data.availability else []
    
    # 3. Calculate upfront fees from Admin settings
    charges = await get_service_charges()
    platform_charge = charges["platform_charge"]
    priority_charge = charges["priority_charge"] if data.isPriority else 0.0
    total_charge = platform_charge + priority_charge
    
    # 4. Create Stripe payment intent if total charge > 0
    intent_id = None
    client_secret = None
    customer_id = None
    ephemeral_key = None
    payment_status = PaymentStatus.PENDING
    initial_status = ServiceStatus.DRAFT
    priority_expiry = None

    if total_charge > 0:
        try:
            customer_id = await get_or_create_stripe_customer(provider_id)
            ephemeral_key = await create_ephemeral_key(customer_id)
            intent = await create_payment_intent(
                amount=total_charge,
                is_escrow=False,
                metadata={"provider_id": str(provider_id), "type": "SERVICE_CREATION_FEE"},
                customer_id=customer_id
            )
            intent_id = intent.id
            client_secret = intent.client_secret
        except Exception as e:
            # If Stripe is unconfigured in local development, handle gracefully or raise
            print(f"Warning: Stripe PaymentIntent creation warning: {e}")
    else:
        # Free service creation if charges are $0
        payment_status = PaymentStatus.PAID
        initial_status = ServiceStatus.PUBLISHED
        if data.isPriority:
            priority_expiry = datetime.now(timezone.utc) + timedelta(hours=24)

    # 5. Create Service in DB
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
            "status": initial_status,
            "isPriority": data.isPriority,
            "priorityExpiresAt": priority_expiry,
            "platformFeePaid": 0.0,
            "priorityFeePaid": 0.0,
            "totalChargePaid": 0.0,
            "stripeIntentId": intent_id,
            "paymentStatus": payment_status
        },
        include={"provider": {"include": {"profile": True}}}
    )
    
    # If free / published immediately, notify past clients
    if initial_status == ServiceStatus.PUBLISHED:
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

    return {
        "service": format_service_response(service),
        "platform_charge": platform_charge,
        "priority_charge": priority_charge,
        "total_charge": total_charge,
        "client_secret": client_secret,
        "customer_id": customer_id,
        "ephemeral_key": ephemeral_key,
        "payment_required": total_charge > 0 and payment_status == PaymentStatus.PENDING
    }

async def confirm_service_payment(provider_id: int, service_id: int):
    """
    Confirms upfront Stripe payment for a service, transitioning it to PUBLISHED status.
    """
    service = await db.service.find_unique(
        where={"id": service_id},
        include={"provider": {"include": {"profile": True}}}
    )
    if not service or service.providerId != provider_id:
        raise HTTPException(status_code=404, detail="Service not found or unauthorized")
        
    if service.paymentStatus == PaymentStatus.PAID:
        return format_service_response(service)
        
    if not service.stripeIntentId:
        raise HTTPException(status_code=400, detail="No payment intent associated with this service")
        
    # Verify with Stripe
    import stripe
    get_stripe_api_key()
    try:
        intent = stripe.PaymentIntent.retrieve(service.stripeIntentId)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")
        
    if intent.status not in ["succeeded", "processing"]:
        raise HTTPException(
            status_code=400,
            detail=f"Payment has not succeeded yet (Current status: {intent.status})"
        )
        
    # Calculate charges from intent or settings
    charges = await get_service_charges()
    platform_charge = charges["platform_charge"]
    priority_charge = charges["priority_charge"] if service.isPriority else 0.0
    amount_paid = (intent.amount / 100.0) if hasattr(intent, "amount") and intent.amount else (platform_charge + priority_charge)

    priority_expiry = datetime.now(timezone.utc) + timedelta(hours=24) if service.isPriority else None
    
    updated_service = await db.service.update(
        where={"id": service_id},
        data={
            "status": ServiceStatus.PUBLISHED,
            "paymentStatus": PaymentStatus.PAID,
            "platformFeePaid": platform_charge,
            "priorityFeePaid": priority_charge,
            "totalChargePaid": amount_paid,
            "priorityExpiresAt": priority_expiry
        },
        include={"provider": {"include": {"profile": True}}}
    )
    
    # Record transaction in Transaction table
    try:
        from prisma.enums import TransactionType, TransactionStatus
        await db.transaction.create(
            data={
                "amount": amount_paid,
                "type": TransactionType.PAYMENT,
                "status": TransactionStatus.COMPLETED,
                "stripeChargeId": getattr(intent, "latest_charge", None) or intent.id,
                "userId": provider_id
            }
        )
    except Exception as e:
        print(f"Warning: Transaction record creation notice: {e}")
        
    # Notify Past Clients
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
            description=f"Your previous service provider has published a new service: '{updated_service.title}'",
            notification_type="new_service",
            image=updated_service.images[0] if updated_service.images else None
        )
        
    return format_service_response(updated_service)


async def get_provider_services(provider_id: int, status_filter: str = "ALL", page: int = 1, page_size: int = 10):
    """
    Returns all services belonging to a specific provider with pagination and extra provider statistics.
    """
    where = {"providerId": provider_id}
    if status_filter != "ALL":
        where["status"] = status_filter
        
    total = await db.service.count(where=where)
    
    # 1. Counts for the whole provider (regardless of filter)
    all_provider_services = await db.service.find_many(where={"providerId": provider_id})
    total_published = sum(1 for s in all_provider_services if s.status == ServiceStatus.PUBLISHED)
    total_draft = sum(1 for s in all_provider_services if s.status == ServiceStatus.DRAFT)
    total_paused = sum(1 for s in all_provider_services if s.status == ServiceStatus.PAUSED)
    total_closed = sum(1 for s in all_provider_services if s.status == ServiceStatus.CLOSED)
    
    # 2. Get Average Rating from ProviderStats
    stats = await db.providerstats.find_unique(where={"providerId": provider_id})
    average_rating = stats.averageRating if stats else 0.0

    # 3. Get Total Pending Requests from Users
    from prisma.enums import ApplicationStatus
    total_pending_requests = await db.serviceapplication.count(
        where={
            "service": {"providerId": provider_id},
            "status": ApplicationStatus.PENDING
        }
    )
    
    # 4. Fetch Paginated Services
    services = await db.service.find_many(
        where=where,
        include={"provider": {"include": {"profile": True}}},
        order={"createdAt": "desc"},
        skip=(page - 1) * page_size,
        take=page_size
    )
        
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "average_rating": average_rating,
        "total_published": total_published,
        "total_draft": total_draft,
        "total_paused": total_paused,
        "total_closed": total_closed,
        "total_pending_requests": total_pending_requests,
        "services": [format_service_response(s) for s in services]
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
    
    # Auto-expire priority services whose 24-hour boost has elapsed
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    expired_services = await db.service.find_many(
        where={
            "isPriority": True,
            "priorityExpiresAt": {"lte": now}
        }
    )
    for es in expired_services:
        await db.service.update(where={"id": es.id}, data={"isPriority": False})

    services = await db.service.find_many(
        where=query,
        include={"provider": {"include": {"profile": True}}},
        order=[{"isPriority": "desc"}, {"createdAt": "desc"}],
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
    If publishing a draft or enabling priority when payment is pending, creates a Stripe PaymentIntent
    and returns client_secret, customer_id, and ephemeral_key for Stripe PaymentSheet.
    """
    service = await db.service.find_unique(
        where={"id": service_id},
        include={"provider": {"include": {"profile": True}}}
    )
    
    if not service or service.providerId != provider_id:
        raise HTTPException(status_code=404, detail="Service not found or access denied")
        
    update_data = data.model_dump(exclude_unset=True)
    
    if "category" in update_data:
        update_data["category"] = update_data["category"].strip() if update_data["category"] else None
        
    if "requirements" in update_data and update_data["requirements"]:
        update_data["requirements"] = Json([r for r in update_data["requirements"]])
        
    if "availability" in update_data and update_data["availability"]:
        update_data["availability"] = Json(update_data["availability"])

    # Determine target priority and status
    target_is_priority = data.isPriority if data.isPriority is not None else service.isPriority
    target_status = data.status if data.status is not None else service.status

    platform_charge = 0.0
    priority_charge = 0.0
    total_charge = 0.0

    charges = await get_service_charges()

    # If service payment is still PENDING
    if service.paymentStatus != PaymentStatus.PAID:
        # If user explicitly wants to keep/save as DRAFT without publishing:
        if data.status == ServiceStatus.DRAFT:
            total_charge = 0.0
        else:
            # Publish requested, or updating an unpaid draft
            platform_charge = charges["platform_charge"]
            if target_is_priority:
                priority_charge = charges["priority_charge"]
            total_charge = platform_charge + priority_charge
    else:
        # If service was already PAID, but now newly enabling priority
        if target_is_priority and not service.isPriority:
            priority_charge = charges["priority_charge"]
            total_charge = priority_charge

    # Stripe credentials for PaymentSheet
    intent_id = None
    client_secret = None
    customer_id = None
    ephemeral_key = None
    payment_required = False

    if total_charge > 0:
        payment_required = True
        try:
            customer_id = await get_or_create_stripe_customer(provider_id)
            ephemeral_key = await create_ephemeral_key(customer_id)
            intent = await create_payment_intent(
                amount=total_charge,
                is_escrow=False,
                metadata={
                    "provider_id": str(provider_id),
                    "service_id": str(service_id),
                    "type": "SERVICE_CREATION_FEE"
                },
                customer_id=customer_id
            )
            intent_id = intent.id
            client_secret = intent.client_secret
        except Exception as e:
            print(f"Warning: Stripe PaymentIntent creation warning: {e}")

        # Keep status as DRAFT in DB until payment confirmation
        update_data["status"] = ServiceStatus.DRAFT
        update_data["stripeIntentId"] = intent_id
        update_data["paymentStatus"] = PaymentStatus.PENDING
        update_data["isPriority"] = target_is_priority
    else:
        # If no charge required and target status is PUBLISHED
        if target_status == ServiceStatus.PUBLISHED and service.paymentStatus != PaymentStatus.PAID:
            update_data["status"] = ServiceStatus.PUBLISHED
            update_data["paymentStatus"] = PaymentStatus.PAID
            if target_is_priority:
                update_data["priorityExpiresAt"] = datetime.now(timezone.utc) + timedelta(hours=24)

    updated_service = await db.service.update(
        where={"id": service_id},
        data=update_data, # type: ignore
        include={"provider": {"include": {"profile": True}}}
    )
    
    return {
        "service": format_service_response(updated_service),
        "platform_charge": platform_charge,
        "priority_charge": priority_charge,
        "total_charge": total_charge,
        "client_secret": client_secret,
        "customer_id": customer_id,
        "ephemeral_key": ephemeral_key,
        "payment_required": payment_required
    }

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

async def get_published_service_categories():
    """
    Returns a unique list of categories for all PUBLISHED services.
    """
    # Using Prisma's group_by to get unique category names
    grouped = await db.service.group_by(
        by=["category"],
        where={
            "status": ServiceStatus.PUBLISHED,
            "category": {"not": None}
        }
    )
    
    categories = [item["category"] for item in grouped if item["category"]]
    
    return {"categories": categories}

async def search_services(
    query_str: Optional[str] = None,
    category: Optional[str] = None,
    page: int = 1,
    page_size: int = 10
):
    """
    Search for PUBLISHED services.
    Matches any word from query_str in title OR description (case-insensitive).
    Optionally filters by category name.
    """
    # 1. Start with PUBLISHED services
    query = {"status": ServiceStatus.PUBLISHED}

    # 2. Add Category Filter if provided
    if category is not None:
        query["category"] = category.strip()

    # 3. Add Any Word Matching Query Filter
    if query_str and query_str.strip():
        words = query_str.strip().split()
        or_conditions = []
        for word in words:
            or_conditions.append({"title": {"contains": word, "mode": "insensitive"}})
            or_conditions.append({"description": {"contains": word, "mode": "insensitive"}})
        query["OR"] = or_conditions

    # 4. Get Total Count
    total_count = await db.service.count(where=query)

    # 5. Get Paginated Services
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
