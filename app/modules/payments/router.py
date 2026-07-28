from fastapi import APIRouter, Depends, HTTPException, Request, Header
import stripe
import os
from .schemas import (
    CheckoutProductRequest,
    CheckoutServiceRequest,
    RefundRequest,
    CreateOnboardingLinkRequest,
    StripeConnectStatusResponse,
    OnboardingLinkResponse
)
from .service import (
    create_payment_intent,
    capture_escrow_intent,
    refund_payment,
    create_stripe_connect_account,
    create_connect_onboarding_link,
    retrieve_connect_account_status,
    create_stripe_dashboard_login_link,
    transfer_to_connected_account
)
from app.modules.users.router import get_current_user_id
from app.core.pricing_engine import (
    calculate_platform_fee,
    calculate_protection_fee,
    calculate_escrow_fee,
    calculate_delivery_fee
)
from app.core.db import db
from prisma.enums import PaymentMethod, PaymentStatus

router = APIRouter(prefix="/payments", tags=["Payments"])

@router.post("/checkout/product")
async def checkout_product(req: CheckoutProductRequest, current_user_id: int = Depends(get_current_user_id)):
    product = await db.product.find_unique(where={"id": req.product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
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
    payment_status = PaymentStatus.PENDING
    payment_method = PaymentMethod.STRIPE
    
    if req.is_cod:
        # COD Flow
        total_amount = subtotal # No fees for COD MVP
        platform_fee = protection_fee = escrow_fee = 0.0
        payment_method = PaymentMethod.COD
    else:
        # Stripe Flow
        intent = await create_payment_intent(
            amount=total_amount, 
            is_escrow=req.is_escrow,
            metadata={"product_id": req.product_id, "user_id": current_user_id}
        )
        intent_id = intent.id
        client_secret = intent.client_secret
        if req.is_escrow:
            payment_status = PaymentStatus.HELD_IN_ESCROW
            
    # Create the order
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
            "hasProtection": req.has_protection,
            "isEscrow": req.is_escrow,
            "isCOD": req.is_cod
        }
    )
    
    return {
        "order": order,
        "client_secret": client_secret
    }

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
    payment_status = PaymentStatus.PENDING
    payment_method = PaymentMethod.STRIPE
    
    if req.is_cod:
        total_amount = subtotal # No fees for COD MVP
        platform_fee = protection_fee = escrow_fee = 0.0
        payment_method = PaymentMethod.COD
    else:
        intent = await create_payment_intent(
            amount=total_amount, 
            is_escrow=req.is_escrow,
            metadata={"service_application_id": req.service_application_id, "user_id": current_user_id}
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
        "client_secret": client_secret
    }

@router.post("/escrow/{order_id}/release")
async def release_escrow(order_id: int, current_user_id: int = Depends(get_current_user_id)):
    order = await db.order.find_unique(
        where={"id": order_id},
        include={"product": {"include": {"seller": True}}}
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    if order.paymentStatus != PaymentStatus.HELD_IN_ESCROW or not order.stripeIntentId:
        raise HTTPException(status_code=400, detail="Order is not held in escrow")
        
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
        data={"paymentStatus": PaymentStatus.PAID}
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
        refresh_url=req.refresh_url or "https://jordencuz.com/stripe/connect/refresh",
        return_url=req.return_url or "https://jordencuz.com/stripe/connect/return"
    )
    
    return {
        "onboarding_url": onboarding_url,
        "stripe_account_id": account_id
    }

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
            # Log Transaction
            await db.transaction.create(data={
                "amount": float(data_object['amount_received']) / 100,
                "currency": data_object['currency'],
                "type": "PAYMENT",
                "status": "COMPLETED",
                "stripeChargeId": data_object.get("latest_charge"),
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
            
    elif event_type == 'charge.refunded':
        intent_id = data_object['payment_intent']
        order = await db.order.find_first(where={"stripeIntentId": intent_id})
        if order:
            await db.order.update(
                where={"id": order.id},
                data={"paymentStatus": PaymentStatus.REFUNDED}
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

    return {"status": "success"}

