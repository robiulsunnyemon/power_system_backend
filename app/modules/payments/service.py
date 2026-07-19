import stripe
import os
from fastapi import HTTPException
from app.core.db import db
from prisma.enums import PaymentStatus

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

async def create_payment_intent(amount: float, currency: str = "usd", is_escrow: bool = False, metadata: dict = None):
    try:
        amount_cents = int(amount * 100)
        
        intent_kwargs = {
            "amount": amount_cents,
            "currency": currency,
            "metadata": metadata or {},
        }
        
        # If Escrow, we only authorize the charge. We capture it later.
        if is_escrow:
            intent_kwargs["capture_method"] = "manual"
            
        intent = stripe.PaymentIntent.create(**intent_kwargs)
        return intent
    except stripe.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))

async def capture_escrow_intent(intent_id: str):
    try:
        intent = stripe.PaymentIntent.retrieve(intent_id)
        if intent.status == "requires_capture":
            intent = stripe.PaymentIntent.capture(intent_id)
        return intent
    except stripe.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))

async def refund_payment(intent_id: str, amount: float = None):
    try:
        refund_kwargs = {"payment_intent": intent_id}
        if amount is not None:
            refund_kwargs["amount"] = int(amount * 100)
            
        refund = stripe.Refund.create(**refund_kwargs)
        return refund
    except stripe.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))
