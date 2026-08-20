import stripe
import os
from fastapi import HTTPException
from app.core.db import db
from prisma.enums import PaymentStatus
from app.core.config import get_settings

def get_stripe_api_key():
    key = os.getenv("STRIPE_SECRET_KEY") or get_settings().STRIPE_SECRET_KEY
    if key:
        stripe.api_key = key
    return key

# Set Stripe API key on module load
try:
    get_stripe_api_key()
except Exception:
    pass

async def create_payment_intent(amount: float, currency: str = "usd", is_escrow: bool = False, metadata: dict = None):
    get_stripe_api_key()
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
    get_stripe_api_key()
    try:
        intent = stripe.PaymentIntent.retrieve(intent_id)
        if intent.status == "requires_capture":
            intent = stripe.PaymentIntent.capture(intent_id)
        return intent
    except stripe.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))

async def refund_payment(intent_id: str, amount: float = None):
    get_stripe_api_key()
    try:
        refund_kwargs = {"payment_intent": intent_id}
        if amount is not None:
            refund_kwargs["amount"] = int(amount * 100)
            
        refund = stripe.Refund.create(**refund_kwargs)
        return refund
    except stripe.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))

async def create_stripe_connect_account(user_id: int, email: str, country: str = "US"):
    get_stripe_api_key()
    try:
        account = stripe.Account.create(
            type="express",
            country=country,
            email=email,
            capabilities={
                "card_payments": {"requested": True},
                "transfers": {"requested": True},
            },
            metadata={"user_id": str(user_id)}
        )
        return account
    except stripe.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))

async def create_connect_onboarding_link(account_id: str, refresh_url: str, return_url: str):
    get_stripe_api_key()
    try:
        account_link = stripe.AccountLink.create(
            account=account_id,
            refresh_url=refresh_url,
            return_url=return_url,
            type="account_onboarding",
        )
        return account_link.url
    except stripe.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))

async def retrieve_connect_account_status(account_id: str):
    get_stripe_api_key()
    try:
        account = stripe.Account.retrieve(account_id)
        payouts_enabled = getattr(account, "payouts_enabled", False)
        charges_enabled = getattr(account, "charges_enabled", False)
        details_submitted = getattr(account, "details_submitted", False)
        
        status = "PENDING"
        if payouts_enabled and charges_enabled:
            status = "CONNECTED"
        elif details_submitted:
            status = "VERIFYING"
            
        return {
            "payouts_enabled": payouts_enabled,
            "charges_enabled": charges_enabled,
            "details_submitted": details_submitted,
            "status": status
        }
    except stripe.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))

async def create_stripe_dashboard_login_link(account_id: str):
    get_stripe_api_key()
    try:
        link = stripe.Account.create_login_link(account_id)
        return link.url
    except stripe.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))

async def transfer_to_connected_account(amount: float, destination_account_id: str, currency: str = "usd", transfer_group: str = None):
    get_stripe_api_key()
    try:
        amount_cents = int(amount * 100)
        transfer_kwargs = {
            "amount": amount_cents,
            "currency": currency,
            "destination": destination_account_id,
        }
        if transfer_group:
            transfer_kwargs["transfer_group"] = transfer_group
            
        transfer = stripe.Transfer.create(**transfer_kwargs)
        return transfer
    except stripe.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))

