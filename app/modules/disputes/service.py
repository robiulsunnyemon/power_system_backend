from fastapi import HTTPException
from app.core.db import db
from prisma.enums import DisputeStatus, DisputeType, PaymentStatus
from app.modules.disputes.schemas import CreateDisputeRequest, ResolveDisputeRequest
from app.modules.admin.service import (
    admin_process_refund,
    admin_force_release_order_escrow,
    admin_force_release_service_escrow
)

def _format_dispute(d):
    initiator_info = {
        "id": d.initiator.id if d.initiator else 0,
        "fullname": d.initiator.fullname if d.initiator else "Unknown",
        "email": d.initiator.email if d.initiator else ""
    }
    respondent_info = {
        "id": d.respondent.id if d.respondent else 0,
        "fullname": d.respondent.fullname if d.respondent else "Unknown",
        "email": d.respondent.email if d.respondent else ""
    }

    order_title = None
    order_amount = None
    if d.order:
        order_title = d.order.product.title if d.order.product else f"Order #{d.order.id}"
        order_amount = d.order.totalAmount

    service_title = None
    service_amount = None
    if d.serviceApplication:
        service_title = d.serviceApplication.service.title if d.serviceApplication.service else f"Service App #{d.serviceApplication.id}"
        service_amount = d.serviceApplication.totalAmount

    return {
        "id": d.id,
        "disputeType": d.disputeType,
        "reason": d.reason,
        "description": d.description,
        "evidenceImages": d.evidenceImages or [],
        "status": d.status,
        "adminNotes": d.adminNotes,
        "orderId": d.orderId,
        "order_title": order_title,
        "order_amount": order_amount,
        "serviceApplicationId": d.serviceApplicationId,
        "service_title": service_title,
        "service_amount": service_amount,
        "initiator": initiator_info,
        "respondent": respondent_info,
        "createdAt": d.createdAt,
        "updatedAt": d.updatedAt
    }

async def create_order_dispute(user_id: int, order_id: int, data: CreateDisputeRequest):
    order = await db.order.find_unique(
        where={"id": order_id},
        include={"product": True}
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    is_buyer = order.userId == user_id
    is_seller = order.product and order.product.sellerId == user_id
    if not is_buyer and not is_seller:
        raise HTTPException(status_code=403, detail="You are not a participant in this order")

    respondent_id = order.product.sellerId if is_buyer else order.userId

    # Check for existing open dispute
    existing = await db.dispute.find_first(
        where={
            "orderId": order_id,
            "status": {"in": [DisputeStatus.OPEN, DisputeStatus.UNDER_REVIEW]}
        }
    )
    if existing:
        raise HTTPException(status_code=400, detail="An active dispute already exists for this order")

    dispute = await db.dispute.create(
        data={
            "disputeType": DisputeType.ORDER,
            "reason": data.reason,
            "description": data.description,
            "evidenceImages": data.evidenceImages or [],
            "status": DisputeStatus.OPEN,
            "orderId": order_id,
            "initiatorId": user_id,
            "respondentId": respondent_id
        },
        include={
            "initiator": True,
            "respondent": True,
            "order": {"include": {"product": True}}
        }
    )

    return _format_dispute(dispute)

async def create_service_dispute(user_id: int, service_app_id: int, data: CreateDisputeRequest):
    service_app = await db.serviceapplication.find_unique(
        where={"id": service_app_id},
        include={"service": True}
    )
    if not service_app:
        raise HTTPException(status_code=404, detail="Service application not found")

    is_client = service_app.clientId == user_id
    is_provider = service_app.service and service_app.service.providerId == user_id
    if not is_client and not is_provider:
        raise HTTPException(status_code=403, detail="You are not a participant in this service application")

    respondent_id = service_app.service.providerId if is_client else service_app.clientId

    existing = await db.dispute.find_first(
        where={
            "serviceApplicationId": service_app_id,
            "status": {"in": [DisputeStatus.OPEN, DisputeStatus.UNDER_REVIEW]}
        }
    )
    if existing:
        raise HTTPException(status_code=400, detail="An active dispute already exists for this service application")

    dispute = await db.dispute.create(
        data={
            "disputeType": DisputeType.SERVICE,
            "reason": data.reason,
            "description": data.description,
            "evidenceImages": data.evidenceImages or [],
            "status": DisputeStatus.OPEN,
            "serviceApplicationId": service_app_id,
            "initiatorId": user_id,
            "respondentId": respondent_id
        },
        include={
            "initiator": True,
            "respondent": True,
            "serviceApplication": {"include": {"service": True}}
        }
    )

    return _format_dispute(dispute)

async def get_user_disputes(user_id: int, page: int = 1, page_size: int = 10):
    query = {
        "OR": [
            {"initiatorId": user_id},
            {"respondentId": user_id}
        ]
    }
    total = await db.dispute.count(where=query)
    disputes = await db.dispute.find_many(
        where=query,
        include={
            "initiator": True,
            "respondent": True,
            "order": {"include": {"product": True}},
            "serviceApplication": {"include": {"service": True}}
        },
        skip=(page - 1) * page_size,
        take=page_size,
        order={"createdAt": "desc"}
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "disputes": [_format_dispute(d) for d in disputes]
    }

async def get_admin_disputes(status: DisputeStatus = None, dispute_type: DisputeType = None, page: int = 1, page_size: int = 10):
    query = {}
    if status:
        query["status"] = status
    if dispute_type:
        query["disputeType"] = dispute_type

    total = await db.dispute.count(where=query)
    disputes = await db.dispute.find_many(
        where=query,
        include={
            "initiator": True,
            "respondent": True,
            "order": {"include": {"product": True}},
            "serviceApplication": {"include": {"service": True}}
        },
        skip=(page - 1) * page_size,
        take=page_size,
        order={"createdAt": "desc"}
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "disputes": [_format_dispute(d) for d in disputes]
    }

async def get_dispute_by_id(dispute_id: int):
    dispute = await db.dispute.find_unique(
        where={"id": dispute_id},
        include={
            "initiator": True,
            "respondent": True,
            "order": {"include": {"product": True}},
            "serviceApplication": {"include": {"service": True}}
        }
    )
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")
    return _format_dispute(dispute)

async def resolve_dispute(dispute_id: int, req: ResolveDisputeRequest, admin_id: int = None):
    dispute = await db.dispute.find_unique(
        where={"id": dispute_id},
        include={
            "initiator": True,
            "respondent": True,
            "order": {"include": {"product": True}},
            "serviceApplication": {"include": {"service": True}}
        }
    )
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")

    # Update dispute status
    updated = await db.dispute.update(
        where={"id": dispute_id},
        data={
            "status": req.status,
            "adminNotes": req.adminNotes
        },
        include={
            "initiator": True,
            "respondent": True,
            "order": {"include": {"product": True}},
            "serviceApplication": {"include": {"service": True}}
        }
    )

    # Perform automated payout / refund actions if requested
    if req.execute_action:
        if req.status == DisputeStatus.RESOLVED_BUYER_REFUNDED:
            if dispute.orderId:
                await admin_process_refund(
                    order_id=dispute.orderId,
                    reason=f"Dispute #{dispute_id} Resolution: Buyer Refund - {req.adminNotes}",
                    admin_id=admin_id
                )
            elif dispute.serviceApplicationId:
                await admin_process_refund(
                    service_application_id=dispute.serviceApplicationId,
                    reason=f"Dispute #{dispute_id} Resolution: Client Refund - {req.adminNotes}",
                    admin_id=admin_id
                )

        elif req.status == DisputeStatus.RESOLVED_SELLER_PAID:
            if dispute.orderId:
                await admin_force_release_order_escrow(order_id=dispute.orderId, admin_id=admin_id)
            elif dispute.serviceApplicationId:
                await admin_force_release_service_escrow(service_app_id=dispute.serviceApplicationId, admin_id=admin_id)

    return _format_dispute(updated)
