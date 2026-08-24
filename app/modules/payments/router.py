from fastapi import APIRouter, Depends, HTTPException, Request, Header
from fastapi.responses import HTMLResponse
import stripe
import os
from datetime import datetime, timedelta, timezone
from .schemas import (
    CheckoutProductRequest,
    CheckoutServiceRequest,
    RefundRequest,
    CreateOnboardingLinkRequest,
    StripeConnectStatusResponse,
    OnboardingLinkResponse,
    PriorityBoostProductRequest,
    PriorityBoostServiceRequest,
    PriorityBoostUrgentJobRequest
)
from .service import (
    create_payment_intent,
    capture_escrow_intent,
    refund_payment,
    create_stripe_connect_account,
    create_connect_onboarding_link,
    retrieve_connect_account_status,
    create_stripe_dashboard_login_link,
    transfer_to_connected_account,
    get_or_create_stripe_customer,
    create_ephemeral_key
)
from app.modules.users.router import get_current_user_id
from app.core.pricing_engine import (
    calculate_platform_fee,
    calculate_protection_fee,
    calculate_escrow_fee,
    calculate_delivery_fee,
    PRODUCT_PRIORITY_FEE,
    SERVICE_PRIORITY_FEE,
    URGENT_JOB_PRIORITY_FEE,
    PRIORITY_DURATION_HOURS
)
from app.core.db import db
from prisma.enums import PaymentMethod, PaymentStatus, ProductStatus, OrderStatus

router = APIRouter(prefix="/payments", tags=["Payments"])

@router.post("/checkout/product")
async def checkout_product(req: CheckoutProductRequest, current_user_id: int = Depends(get_current_user_id)):
    product = await db.product.find_unique(where={"id": req.product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if product.status != ProductStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="This product is already sold or unavailable")
        
    if product.sellerId == current_user_id:
        raise HTTPException(status_code=400, detail="You cannot purchase your own product")
        
    subtotal = product.price
    platform_fee = calculate_platform_fee(subtotal, "PRODUCT")
    protection_fee = calculate_protection_fee(subtotal) if req.has_protection else 0.0
    escrow_fee = calculate_escrow_fee(subtotal) if req.is_escrow else 0.0
    
    item_size_str = "SMALL"
    if product.itemSize:
        item_size_str = getattr(product.itemSize, "name", str(product.itemSize))

    delivery_fee = calculate_delivery_fee(
        size=item_size_str, 
        distance_km=req.distance_km or 0.0, 
        addons=req.delivery_addons or []
    )
    
    total_amount = subtotal + platform_fee + protection_fee + escrow_fee + delivery_fee
    
    intent_id = None
    client_secret = None
    customer_id = None
    ephemeral_key = None
    payment_status = PaymentStatus.PENDING
    payment_method = PaymentMethod.STRIPE
    
    if req.is_cod:
        # COD Flow
        total_amount = subtotal # No fees for COD MVP
        platform_fee = protection_fee = escrow_fee = 0.0
        payment_method = PaymentMethod.COD
    else:
        # Stripe Flow
        customer_id = await get_or_create_stripe_customer(current_user_id)
        ephemeral_key = await create_ephemeral_key(customer_id)
        intent = await create_payment_intent(
            amount=total_amount, 
            is_escrow=req.is_escrow,
            metadata={"product_id": req.product_id, "user_id": current_user_id},
            customer_id=customer_id
        )
        intent_id = intent.id
        client_secret = intent.client_secret
        if req.is_escrow:
            payment_status = PaymentStatus.HELD_IN_ESCROW
            
    # Create the order with complete delivery info
    order = await db.order.create(
        data={
            "userId": current_user_id,
            "productId": req.product_id,
            "subTotal": subtotal,
            "platformFee": platform_fee,
            "protectionFee": protection_fee,
            "escrowFee": escrow_fee,
            "deliveryFee": delivery_fee,
            "totalAmount": total_amount,
            "paymentMethod": payment_method,
            "paymentStatus": payment_status,
            "stripeIntentId": intent_id,
            "distanceKm": req.distance_km,
            "deliveryAddons": req.delivery_addons,
            "deliveryAddress": req.delivery_address,
            "deliveryCity": req.delivery_city,
            "recipientName": req.recipient_name,
            "recipientPhone": req.recipient_phone,
            "deliveryInstructions": req.delivery_instructions,
            "hasProtection": req.has_protection,
            "isEscrow": req.is_escrow,
            "isCOD": req.is_cod
        }
    )
    
    # For COD orders, mark product SOLDOUT immediately upon order placement
    if req.is_cod:
        await db.product.update(
            where={"id": product.id},
            data={"status": ProductStatus.SOLDOUT}
        )
    
    return {
        "order": order,
        "client_secret": client_secret,
        "customer_id": customer_id,
        "ephemeral_key": ephemeral_key
    }

@router.post("/checkout/cancel")
async def cancel_checkout(order_id: int, current_user_id: int = Depends(get_current_user_id)):
    """
    Cancels a pending checkout session and ensures the product remains ACTIVE.
    """
    order = await db.order.find_first(
        where={"id": order_id, "userId": current_user_id}
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.paymentStatus == PaymentStatus.PENDING:
        await db.order.update(
            where={"id": order.id},
            data={"status": OrderStatus.CANCELLED, "paymentStatus": PaymentStatus.FAILED}
        )
        if order.productId:
            await db.product.update(
                where={"id": order.productId},
                data={"status": ProductStatus.ACTIVE}
            )
    return {"status": "success", "message": "Checkout session cancelled"}

@router.post("/checkout/service")
async def checkout_service(req: CheckoutServiceRequest, current_user_id: int = Depends(get_current_user_id)):
    service_app = await db.serviceapplication.find_unique(
        where={"id": req.service_application_id},
        include={"service": True}
    )
    if not service_app:
        raise HTTPException(status_code=404, detail="Service application not found")
        
    if service_app.service.providerId != current_user_id:
        raise HTTPException(status_code=403, detail="Only the job poster (Service Provider) can pay for this service.")
        
    subtotal = service_app.proposedRate
    platform_fee = calculate_platform_fee(subtotal, "SERVICE")
    protection_fee = calculate_protection_fee(subtotal) if req.has_protection else 0.0
    escrow_fee = calculate_escrow_fee(subtotal) if req.is_escrow else 0.0
    
    total_amount = subtotal + platform_fee + protection_fee + escrow_fee
    
    intent_id = None
    client_secret = None
    customer_id = None
    ephemeral_key = None
    payment_status = PaymentStatus.PENDING
    payment_method = PaymentMethod.STRIPE
    
    if req.is_cod:
        total_amount = subtotal # No fees for COD MVP
        platform_fee = protection_fee = escrow_fee = 0.0
        payment_method = PaymentMethod.COD
    else:
        customer_id = await get_or_create_stripe_customer(current_user_id)
        ephemeral_key = await create_ephemeral_key(customer_id)
        intent = await create_payment_intent(
            amount=total_amount, 
            is_escrow=req.is_escrow,
            metadata={"service_application_id": req.service_application_id, "user_id": current_user_id},
            customer_id=customer_id
        )
        intent_id = intent.id
        client_secret = intent.client_secret
        if req.is_escrow:
            payment_status = PaymentStatus.HELD_IN_ESCROW
            
    # Update the service application
    updated_app = await db.serviceapplication.update(
        where={"id": req.service_application_id},
        data={
            "subTotal": subtotal,
            "platformFee": platform_fee,
            "protectionFee": protection_fee,
            "escrowFee": escrow_fee,
            "totalAmount": total_amount,
            "paymentMethod": payment_method,
            "paymentStatus": payment_status,
            "stripeIntentId": intent_id,
            "hasProtection": req.has_protection,
            "isEscrow": req.is_escrow,
            "isCOD": req.is_cod
        }
    )
    
    return {
        "service_application": updated_app,
        "client_secret": client_secret,
        "customer_id": customer_id,
        "ephemeral_key": ephemeral_key
    }

@router.post("/escrow/{order_id}/release")
async def release_escrow(order_id: int, current_user_id: int = Depends(get_current_user_id)):
    order = await db.order.find_unique(
        where={"id": order_id},
        include={"product": {"include": {"seller": True}}}
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    if order.paymentStatus == PaymentStatus.PAID:
        return {"message": "Order payment has already been released", "order": order}
        
    if order.paymentStatus == PaymentStatus.HELD_IN_ESCROW and order.stripeIntentId:
        await capture_escrow_intent(order.stripeIntentId)
    
    # Auto-payout net earnings to seller if Connect account is active
    seller = order.product.seller if (order.product and order.product.seller) else None
    if seller and seller.stripeAccountId and seller.payoutsEnabled:
        payout_amount = order.subTotal
        try:
            await transfer_to_connected_account(
                amount=payout_amount,
                destination_account_id=seller.stripeAccountId,
                transfer_group=f"ORDER_{order.id}"
            )
        except Exception as e:
            print(f"Warning: Auto payout to seller Stripe Connect account failed: {e}")

    updated = await db.order.update(
        where={"id": order_id},
        data={
            "paymentStatus": PaymentStatus.PAID,
            "status": OrderStatus.DELIVERED,
            "tracking": {
                "create": [{"status": "ORDER COMPLETED & ESCROW RELEASED"}]
            }
        }
    )
    return {"message": "Escrow released successfully and payout processed", "order": updated}

@router.post("/service-escrow/{service_application_id}/release")
async def release_service_escrow(service_application_id: int, current_user_id: int = Depends(get_current_user_id)):
    service_app = await db.serviceapplication.find_unique(
        where={"id": service_application_id},
        include={"client": True, "service": True}
    )
    if not service_app:
        raise HTTPException(status_code=404, detail="Service application not found")
        
    if service_app.paymentStatus != PaymentStatus.HELD_IN_ESCROW or not service_app.stripeIntentId:
        raise HTTPException(status_code=400, detail="Service application payment is not held in escrow")
        
    await capture_escrow_intent(service_app.stripeIntentId)
    
    # Auto-payout net earnings to applicant (client) if Connect account is active
    applicant = service_app.client
    if applicant and applicant.stripeAccountId and applicant.payoutsEnabled:
        payout_amount = service_app.subTotal
        try:
            await transfer_to_connected_account(
                amount=payout_amount,
                destination_account_id=applicant.stripeAccountId,
                transfer_group=f"SERVICE_APP_{service_app.id}"
            )
        except Exception as e:
            print(f"Warning: Auto payout to applicant Stripe Connect account failed: {e}")

    updated = await db.serviceapplication.update(
        where={"id": service_application_id},
        data={"paymentStatus": PaymentStatus.PAID, "status": "COMPLETED"}
    )
    return {"message": "Service escrow released successfully and payout processed", "service_application": updated}

@router.post("/stripe-connect/onboarding-link", response_model=OnboardingLinkResponse)
async def get_stripe_onboarding_link(req: CreateOnboardingLinkRequest, current_user_id: int = Depends(get_current_user_id)):
    user = await db.user.find_unique(where={"id": current_user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    account_id = user.stripeAccountId
    if not account_id:
        connect_account = await create_stripe_connect_account(
            user_id=user.id,
            email=user.email
        )
        account_id = connect_account.id
        await db.user.update(
            where={"id": user.id},
            data={
                "stripeAccountId": account_id,
                "stripeAccountStatus": "PENDING"
            }
        )
        
    onboarding_url = await create_connect_onboarding_link(
        account_id=account_id,
        refresh_url=req.refresh_url or "https://www.powersystem.maktechapp.cloud/payments/stripe-connect/refresh",
        return_url=req.return_url or "https://www.powersystem.maktechapp.cloud/payments/stripe-connect/return"
    )
    
    return {
        "onboarding_url": onboarding_url,
        "stripe_account_id": account_id
    }

@router.get("/stripe-connect/return", response_class=HTMLResponse)
async def stripe_connect_return():
    """
    Landing page when a seller completes Stripe Connect onboarding.
    """
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Stripe Connect Onboarding Complete</title>
        <style>
            body {
                background-color: #121212;
                color: #ffffff;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
                margin: 0;
                padding: 20px;
                box-sizing: border-box;
            }
            .card {
                background-color: #1e1e1e;
                border: 1px solid #333333;
                border-radius: 16px;
                padding: 40px 30px;
                text-align: center;
                max-width: 420px;
                width: 100%;
                box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
            }
            .icon-circle {
                width: 72px;
                height: 72px;
                background-color: rgba(41, 176, 0, 0.15);
                border: 2px solid #29B000;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 24px auto;
            }
            .icon-circle svg {
                width: 36px;
                height: 36px;
                fill: #29B000;
            }
            h1 {
                font-size: 22px;
                font-weight: 700;
                margin-bottom: 12px;
                color: #ffffff;
            }
            p {
                font-size: 14px;
                color: #a0a0a0;
                line-height: 1.6;
                margin-bottom: 28px;
            }
            .btn {
                display: inline-block;
                background-color: #DD9E40;
                color: #000000;
                font-weight: 700;
                padding: 12px 24px;
                border-radius: 24px;
                font-size: 14px;
                text-decoration: none;
                text-transform: uppercase;
                letter-spacing: 1px;
                transition: background-color 0.2s ease;
            }
            .btn:hover {
                background-color: #c98d36;
            }
        </style>
    </head>
    <body>
        <div class="card">
            <div class="icon-circle">
                <svg viewBox="0 0 24 24">
                    <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
                </svg>
            </div>
            <h1>Onboarding Completed!</h1>
            <p>Your Stripe payout account has been configured successfully. You can now receive payments and payouts directly.</p>
            <a href="jordenapp://stripe-connect/return" class="btn">RETURN TO JORDEN APP</a>
        </div>
        <script>
            setTimeout(function() {
                window.location.href = "jordenapp://stripe-connect/return";
            }, 800);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@router.get("/stripe-connect/refresh", response_class=HTMLResponse)
async def stripe_connect_refresh():
    """
    Landing page when a seller's Stripe Connect onboarding session expires or is interrupted.
    """
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Onboarding Session Expired</title>
        <style>
            body {
                background-color: #121212;
                color: #ffffff;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
                margin: 0;
                padding: 20px;
                box-sizing: border-box;
            }
            .card {
                background-color: #1e1e1e;
                border: 1px solid #333333;
                border-radius: 16px;
                padding: 40px 30px;
                text-align: center;
                max-width: 420px;
                width: 100%;
                box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
            }
            .icon-circle {
                width: 72px;
                height: 72px;
                background-color: rgba(221, 158, 64, 0.15);
                border: 2px solid #DD9E40;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 24px auto;
            }
            .icon-circle svg {
                width: 36px;
                height: 36px;
                fill: #DD9E40;
            }
            h1 {
                font-size: 22px;
                font-weight: 700;
                margin-bottom: 12px;
                color: #ffffff;
            }
            p {
                font-size: 14px;
                color: #a0a0a0;
                line-height: 1.6;
                margin-bottom: 28px;
            }
            .btn {
                display: inline-block;
                background-color: #DD9E40;
                color: #000000;
                font-weight: 700;
                padding: 12px 24px;
                border-radius: 24px;
                font-size: 14px;
                text-decoration: none;
                text-transform: uppercase;
                letter-spacing: 1px;
                transition: background-color 0.2s ease;
            }
            .btn:hover {
                background-color: #c98d36;
            }
        </style>
    </head>
    <body>
        <div class="card">
            <div class="icon-circle">
                <svg viewBox="0 0 24 24">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
                </svg>
            </div>
            <h1>Session Expired</h1>
            <p>Your onboarding session has expired or was interrupted. Please return to the Jorden App and tap Connect again to generate a fresh link.</p>
            <a href="jordenapp://stripe-connect/refresh" class="btn">RETURN TO JORDEN APP</a>
        </div>
        <script>
            setTimeout(function() {
                window.location.href = "jordenapp://stripe-connect/refresh";
            }, 800);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@router.get("/stripe-connect/status", response_model=StripeConnectStatusResponse)
async def check_stripe_connect_status(current_user_id: int = Depends(get_current_user_id)):
    user = await db.user.find_unique(where={"id": current_user_id})
    if not user or not user.stripeAccountId:
        return {
            "stripe_account_id": None,
            "stripe_account_status": "NOT_CONNECTED",
            "payouts_enabled": False,
            "charges_enabled": False
        }
        
    status_info = await retrieve_connect_account_status(user.stripeAccountId)
    
    await db.user.update(
        where={"id": user.id},
        data={
            "stripeAccountStatus": status_info["status"],
            "payoutsEnabled": status_info["payouts_enabled"],
            "chargesEnabled": status_info["charges_enabled"]
        }
    )
    
    return {
        "stripe_account_id": user.stripeAccountId,
        "stripe_account_status": status_info["status"],
        "payouts_enabled": status_info["payouts_enabled"],
        "charges_enabled": status_info["charges_enabled"]
    }

@router.post("/stripe-connect/login-link")
async def get_stripe_login_link(current_user_id: int = Depends(get_current_user_id)):
    user = await db.user.find_unique(where={"id": current_user_id})
    if not user or not user.stripeAccountId:
        raise HTTPException(status_code=400, detail="No connected Stripe account found for this user")
        
    login_url = await create_stripe_dashboard_login_link(user.stripeAccountId)
    return {"login_url": login_url}

@router.post("/priority/product")
async def priority_boost_product(req: PriorityBoostProductRequest, current_user_id: int = Depends(get_current_user_id)):
    product = await db.product.find_unique(where={"id": req.product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.sellerId != current_user_id:
        raise HTTPException(status_code=403, detail="Not authorized to boost this product")

    customer_id = await get_or_create_stripe_customer(current_user_id)
    ephemeral_key = await create_ephemeral_key(customer_id)

    fee_amount = PRODUCT_PRIORITY_FEE
    intent = await create_payment_intent(
        amount=fee_amount,
        currency="usd",
        customer_id=customer_id,
        metadata={
            "type": "PRODUCT_PRIORITY_BOOST",
            "product_id": str(product.id),
            "seller_id": str(current_user_id)
        }
    )

    expires_at = datetime.now(timezone.utc) + timedelta(hours=PRIORITY_DURATION_HOURS)
    updated_product = await db.product.update(
        where={"id": product.id},
        data={
            "isPriority": True,
            "priorityExpiresAt": expires_at
        }
    )

    return {
        "status": "success",
        "message": f"Product boosted to Priority for {PRIORITY_DURATION_HOURS} hours",
        "fee_charged": fee_amount,
        "isPriority": True,
        "priorityExpiresAt": expires_at.isoformat(),
        "client_secret": intent.client_secret,
        "customer_id": customer_id,
        "ephemeral_key": ephemeral_key
    }

@router.post("/priority/service")
async def priority_boost_service(req: PriorityBoostServiceRequest, current_user_id: int = Depends(get_current_user_id)):
    service = await db.service.find_unique(where={"id": req.service_id})
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    if service.providerId != current_user_id:
        raise HTTPException(status_code=403, detail="Not authorized to boost this service")

    customer_id = await get_or_create_stripe_customer(current_user_id)
    ephemeral_key = await create_ephemeral_key(customer_id)

    fee_amount = SERVICE_PRIORITY_FEE
    intent = await create_payment_intent(
        amount=fee_amount,
        currency="usd",
        customer_id=customer_id,
        metadata={
            "type": "SERVICE_PRIORITY_BOOST",
            "service_id": str(service.id),
            "provider_id": str(current_user_id)
        }
    )

    expires_at = datetime.now(timezone.utc) + timedelta(hours=PRIORITY_DURATION_HOURS)
    updated_service = await db.service.update(
        where={"id": service.id},
        data={
            "isPriority": True,
            "priorityExpiresAt": expires_at
        }
    )

    return {
        "status": "success",
        "message": f"Service boosted to Priority for {PRIORITY_DURATION_HOURS} hours",
        "fee_charged": fee_amount,
        "isPriority": True,
        "priorityExpiresAt": expires_at.isoformat(),
        "client_secret": intent.client_secret,
        "customer_id": customer_id,
        "ephemeral_key": ephemeral_key
    }

@router.post("/priority/urgent-job")
async def priority_boost_urgent_job(req: PriorityBoostUrgentJobRequest, current_user_id: int = Depends(get_current_user_id)):
    service_app = await db.serviceapplication.find_unique(where={"id": req.service_application_id})
    if not service_app:
        raise HTTPException(status_code=404, detail="Service application not found")
    if service_app.clientId != current_user_id:
        raise HTTPException(status_code=403, detail="Not authorized to boost this application")

    customer_id = await get_or_create_stripe_customer(current_user_id)
    ephemeral_key = await create_ephemeral_key(customer_id)

    fee_amount = URGENT_JOB_PRIORITY_FEE
    intent = await create_payment_intent(
        amount=fee_amount,
        currency="usd",
        customer_id=customer_id,
        metadata={
            "type": "URGENT_JOB_PRIORITY_BOOST",
            "service_application_id": str(service_app.id),
            "client_id": str(current_user_id)
        }
    )

    expires_at = datetime.now(timezone.utc) + timedelta(hours=PRIORITY_DURATION_HOURS)
    await db.serviceapplication.update(
        where={"id": service_app.id},
        data={
            "isEscrow": True
        }
    )
    if service_app.serviceId:
        await db.service.update(
            where={"id": service_app.serviceId},
            data={
                "isPriority": True,
                "priorityExpiresAt": expires_at
            }
        )

    return {
        "status": "success",
        "message": f"Job boosted to Urgent Priority ($10) for {PRIORITY_DURATION_HOURS} hours",
        "fee_charged": fee_amount,
        "isPriority": True,
        "priorityExpiresAt": expires_at.isoformat(),
        "client_secret": intent.client_secret,
        "customer_id": customer_id,
        "ephemeral_key": ephemeral_key
    }

@router.post("/refund")
async def process_refund(req: RefundRequest, current_user_id: int = Depends(get_current_user_id)):
    """
    Enforces Platform Refund Policy:
    - Fully Refundable: Duplicate payments, failed transactions, item not received, provider no-show, approved disputes.
    - Partially Refundable: Partial service completion, agreed settlements.
    - Non-Refundable: Change of mind, failure to inspect, completed services & deliveries, consumed priority fees.
    """
    order = await db.order.find_unique(where={"id": req.order_id})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Non-Refundable Enforcer: Completed deliveries/services are non-refundable
    if order.status == OrderStatus.DELIVERED and order.paymentStatus == PaymentStatus.PAID:
        raise HTTPException(
            status_code=400, 
            detail="Completed deliveries and services are non-refundable according to platform policy."
        )

    if not order.stripeIntentId:
        raise HTTPException(status_code=400, detail="Order has no associated Stripe Payment Intent")

    try:
        refund_res = await refund_payment(order.stripeIntentId, req.amount)
        await db.order.update(
            where={"id": order.id},
            data={"paymentStatus": PaymentStatus.REFUNDED}
        )
        await db.transaction.create(data={
            "amount": req.amount if req.amount else order.totalAmount,
            "currency": "usd",
            "type": "REFUND",
            "status": "COMPLETED",
            "stripeChargeId": str(getattr(refund_res, "id", "")),
            "userId": current_user_id,
            "orderId": order.id
        })
        return {
            "status": "success",
            "message": "Refund processed successfully according to platform policy",
            "refund": refund_res
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Refund failed: {str(e)}")

@router.post("/webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    if not webhook_secret:
        raise HTTPException(status_code=400, detail="Webhook secret not configured")
        
    payload = await request.body()
    
    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, webhook_secret
        )
    except ValueError as e:
        # Invalid payload
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event['type']
    data_object = event['data']['object']
    
    if event_type == 'payment_intent.succeeded':
        intent_id = data_object['id']
        order = await db.order.find_first(where={"stripeIntentId": intent_id})
        if order:
            await db.order.update(
                where={"id": order.id},
                data={"paymentStatus": PaymentStatus.PAID}
            )
            if order.productId:
                await db.product.update(
                    where={"id": order.productId},
                    data={"status": ProductStatus.SOLDOUT}
                )
            # Log Transaction
            await db.transaction.create(data={
                "amount": float(data_object['amount_received']) / 100,
                "currency": data_object['currency'],
                "type": "PAYMENT",
                "status": "COMPLETED",
                "stripeChargeId": getattr(data_object, "latest_charge", None),
                "userId": order.userId,
                "orderId": order.id
            })
            
    elif event_type == 'payment_intent.amount_capturable_updated':
        # This means Escrow hold was successful
        intent_id = data_object['id']
        order = await db.order.find_first(where={"stripeIntentId": intent_id})
        if order and order.isEscrow:
            await db.order.update(
                where={"id": order.id},
                data={"paymentStatus": PaymentStatus.HELD_IN_ESCROW}
            )
            if order.productId:
                await db.product.update(
                    where={"id": order.productId},
                    data={"status": ProductStatus.SOLDOUT}
                )
            
    elif event_type == 'charge.refunded':
        intent_id = data_object['payment_intent']
        order = await db.order.find_first(where={"stripeIntentId": intent_id})
        if order:
            await db.order.update(
                where={"id": order.id},
                data={"paymentStatus": PaymentStatus.REFUNDED, "status": OrderStatus.CANCELLED}
            )
            if order.productId:
                await db.product.update(
                    where={"id": order.productId},
                    data={"status": ProductStatus.ACTIVE}
                )
            # Log Refund Transaction
            await db.transaction.create(data={
                "amount": float(data_object['amount_refunded']) / 100,
                "currency": data_object['currency'],
                "type": "REFUND",
                "status": "COMPLETED",
                "stripeChargeId": data_object['id'],
                "userId": order.userId,
                "orderId": order.id
            })
            
    elif event_type == 'payment_intent.payment_failed':
        intent_id = data_object['id']
        order = await db.order.find_first(where={"stripeIntentId": intent_id})
        if order:
            await db.order.update(
                where={"id": order.id},
                data={"paymentStatus": PaymentStatus.FAILED, "status": OrderStatus.CANCELLED}
            )
            if order.productId:
                await db.product.update(
                    where={"id": order.productId},
                    data={"status": ProductStatus.ACTIVE}
                )
            
    elif event_type == 'charge.dispute.created':
        intent_id = data_object['payment_intent']
        order = await db.order.find_first(where={"stripeIntentId": intent_id})
        if order:
            await db.order.update(
                where={"id": order.id},
                data={"paymentStatus": PaymentStatus.FAILED} # Marking as failed for dispute
            )

    elif event_type == 'account.updated':
        account_id = data_object.get('id')
        payouts_enabled = data_object.get('payouts_enabled', False)
        charges_enabled = data_object.get('charges_enabled', False)
        details_submitted = data_object.get('details_submitted', False)
        
        status = "PENDING"
        if payouts_enabled and charges_enabled:
            status = "CONNECTED"
        elif details_submitted:
            status = "VERIFYING"
            
        user = await db.user.find_first(where={"stripeAccountId": account_id})
        if user:
            await db.user.update(
                where={"id": user.id},
                data={
                    "stripeAccountStatus": status,
                    "payoutsEnabled": payouts_enabled,
                    "chargesEnabled": charges_enabled
                }
            )
            
            # Retroactive Payout: If account just became active, process pending payouts for this user!
            if payouts_enabled and charges_enabled:
                pending_orders = await db.order.find_many(
                    where={
                        "product": {"sellerId": user.id},
                        "paymentStatus": PaymentStatus.PAID
                    }
                )
                for pending_order in pending_orders:
                    try:
                        await transfer_to_connected_account(
                            amount=pending_order.subTotal,
                            destination_account_id=account_id,
                            transfer_group=f"ORDER_{pending_order.id}"
                        )
                    except Exception as ex:
                        print(f"Retroactive payout failed for order {pending_order.id}: {ex}")

                pending_services = await db.serviceapplication.find_many(
                    where={
                        "clientId": user.id,
                        "paymentStatus": PaymentStatus.PAID
                    }
                )
                for pending_svc in pending_services:
                    try:
                        await transfer_to_connected_account(
                            amount=pending_svc.subTotal,
                            destination_account_id=account_id,
                            transfer_group=f"SERVICE_{pending_svc.id}"
                        )
                    except Exception as ex:
                        print(f"Retroactive payout failed for service app {pending_svc.id}: {ex}")

    return {"status": "success"}

