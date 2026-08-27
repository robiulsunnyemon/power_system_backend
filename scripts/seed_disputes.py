import asyncio
import os
import sys

# Add backend root directory to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.db import connect_db, disconnect_db, db
from app.common.security import hash_password
from prisma.enums import (
    Role,
    AccountStatus,
    ProductStatus,
    ProductCondition,
    ItemSize,
    ServiceStatus,
    PricingType,
    OrderStatus,
    ApplicationStatus,
    PaymentMethod,
    PaymentStatus,
    DisputeType,
    DisputeReason,
    DisputeStatus,
)


async def seed_disputes():
    """
    Seeds comprehensive demo data for Disputes:
    - Creates/ensures Buyer, Seller, Service Provider, Client, and Admin users.
    - Creates demo Products, Services, Orders, and Service Applications.
    - Seeds realistic disputes for both `admin/disputes` and `disputes/my` endpoints
      covering various dispute types (ORDER, SERVICE) and statuses (OPEN, UNDER_REVIEW,
      RESOLVED_BUYER_REFUNDED, RESOLVED_SELLER_PAID, REJECTED).
    """
    await connect_db()
    print("\n=======================================================")
    print("  SEEDING DISPUTE DEMO DATA (admin/disputes & disputes/my)")
    print("=======================================================\n")

    hashed_pwd = hash_password("Password123!")

    try:
        # ------------------------------------------------------------------
        # 1. Ensure Admin User
        # ------------------------------------------------------------------
        admin = await db.user.upsert(
            where={"email": "admin@jordencuz.com"},
            data={
                "create": {
                    "fullname": "System Admin",
                    "email": "admin@jordencuz.com",
                    "password": hash_password("AdminPassword123!"),
                    "roles": [Role.ADMIN, Role.USER],
                    "accountStatus": AccountStatus.ACTIVE,
                    "isVerified": True,
                    "isAgreed": True,
                    "lastActiveRole": Role.ADMIN,
                },
                "update": {
                    "accountStatus": AccountStatus.ACTIVE,
                    "roles": [Role.ADMIN, Role.USER],
                },
            },
        )
        print(f"[OK] Admin user verified: {admin.email} (ID: {admin.id})")

        # ------------------------------------------------------------------
        # 2. Ensure Buyer, Seller, Provider, and Client Users
        # ------------------------------------------------------------------
        buyer = await db.user.upsert(
            where={"email": "buyer@test.com"},
            data={
                "create": {
                    "fullname": "Karim Buyer",
                    "email": "buyer@test.com",
                    "password": hashed_pwd,
                    "roles": [Role.USER],
                    "accountStatus": AccountStatus.ACTIVE,
                    "isVerified": True,
                    "isAgreed": True,
                },
                "update": {
                    "accountStatus": AccountStatus.ACTIVE,
                    "isVerified": True,
                },
            },
        )
        await db.userprofile.upsert(
            where={"userId": buyer.id},
            data={
                "create": {"userId": buyer.id, "trust_score": 85.0, "raw_score": 400.0},
                "update": {"trust_score": 85.0},
            },
        )
        print(f"[OK] Buyer user: {buyer.email} (ID: {buyer.id})")

        seller = await db.user.upsert(
            where={"email": "seller@test.com"},
            data={
                "create": {
                    "fullname": "Rahim Seller",
                    "email": "seller@test.com",
                    "password": hashed_pwd,
                    "roles": [Role.USER, Role.SELLER],
                    "accountStatus": AccountStatus.ACTIVE,
                    "isVerified": True,
                    "isAgreed": True,
                    "stripeAccountStatus": "ACTIVE",
                },
                "update": {
                    "accountStatus": AccountStatus.ACTIVE,
                    "roles": [Role.USER, Role.SELLER],
                },
            },
        )
        await db.userprofile.upsert(
            where={"userId": seller.id},
            data={
                "create": {"userId": seller.id, "trust_score": 92.0, "raw_score": 480.0},
                "update": {"trust_score": 92.0},
            },
        )
        print(f"[OK] Seller user: {seller.email} (ID: {seller.id})")

        provider = await db.user.upsert(
            where={"email": "provider@test.com"},
            data={
                "create": {
                    "fullname": "Jamal Provider",
                    "email": "provider@test.com",
                    "password": hashed_pwd,
                    "roles": [Role.USER, Role.SERVICE_PROVIDER],
                    "accountStatus": AccountStatus.ACTIVE,
                    "isVerified": True,
                    "isAgreed": True,
                    "stripeAccountStatus": "ACTIVE",
                },
                "update": {
                    "accountStatus": AccountStatus.ACTIVE,
                    "roles": [Role.USER, Role.SERVICE_PROVIDER],
                },
            },
        )
        await db.userprofile.upsert(
            where={"userId": provider.id},
            data={
                "create": {"userId": provider.id, "trust_score": 88.0, "raw_score": 420.0},
                "update": {"trust_score": 88.0},
            },
        )
        print(f"[OK] Service Provider user: {provider.email} (ID: {provider.id})")

        client = await db.user.upsert(
            where={"email": "client@test.com"},
            data={
                "create": {
                    "fullname": "Amina Client",
                    "email": "client@test.com",
                    "password": hashed_pwd,
                    "roles": [Role.USER],
                    "accountStatus": AccountStatus.ACTIVE,
                    "isVerified": True,
                    "isAgreed": True,
                },
                "update": {
                    "accountStatus": AccountStatus.ACTIVE,
                    "isVerified": True,
                },
            },
        )
        await db.userprofile.upsert(
            where={"userId": client.id},
            data={
                "create": {"userId": client.id, "trust_score": 95.0, "raw_score": 490.0},
                "update": {"trust_score": 95.0},
            },
        )
        print(f"[OK] Client user: {client.email} (ID: {client.id})")

        # ------------------------------------------------------------------
        # 3. Ensure Category & Products
        # ------------------------------------------------------------------
        category = await db.category.find_first()
        if not category:
            category = await db.category.create(data={"name": "Electronics & Gadgets"})

        product_1 = await db.product.create(
            data={
                "title": "Sony WH-1000XM5 Wireless Headphones",
                "description": "Premium noise cancelling wireless over-ear headphones with microphone.",
                "price": 280.0,
                "tax_fee": 14.0,
                "delivery_fee": 10.0,
                "total_fee": 304.0,
                "condition": ProductCondition.NEW,
                "sellerId": seller.id,
                "categoryId": category.id,
                "status": ProductStatus.ACTIVE,
                "itemSize": ItemSize.SMALL,
                "images": ["https://images.unsplash.com/photo-1505740420928-5e560c06d30e"],
            }
        )

        product_2 = await db.product.create(
            data={
                "title": "Vintage Genuine Leather Motorcycle Jacket",
                "description": "Authentic brown distressed biker leather jacket, Size L.",
                "price": 150.0,
                "tax_fee": 7.5,
                "delivery_fee": 15.0,
                "total_fee": 172.5,
                "condition": ProductCondition.USED_LIKE_NEW,
                "sellerId": seller.id,
                "categoryId": category.id,
                "status": ProductStatus.ACTIVE,
                "itemSize": ItemSize.MEDIUM,
                "images": ["https://images.unsplash.com/photo-1551028719-00167b16eac5"],
            }
        )

        product_3 = await db.product.create(
            data={
                "title": "Apple iPad Pro 11-inch M2 128GB",
                "description": "Space Gray iPad Pro with Liquid Retina display.",
                "price": 600.0,
                "tax_fee": 30.0,
                "delivery_fee": 12.0,
                "total_fee": 642.0,
                "condition": ProductCondition.USED_GOOD,
                "sellerId": seller.id,
                "categoryId": category.id,
                "status": ProductStatus.ACTIVE,
                "itemSize": ItemSize.SMALL,
                "images": ["https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0"],
            }
        )
        print(f"[OK] Created 3 Demo Products for Seller")

        # ------------------------------------------------------------------
        # 4. Ensure Services for Provider
        # ------------------------------------------------------------------
        service_1 = await db.service.create(
            data={
                "title": "Residential AC & Appliance Repair Service",
                "description": "Diagnostic and on-site repair for home HVAC, cooling, and refrigeration units.",
                "price": 120.0,
                "pricingType": PricingType.FIXED,
                "providerId": provider.id,
                "status": ServiceStatus.PUBLISHED,
                "category": "Home Repair",
                "images": ["https://images.unsplash.com/photo-1581092160607-ee22621dd758"],
            }
        )

        service_2 = await db.service.create(
            data={
                "title": "Mobile App Architecture & Code Review",
                "description": "Expert 1-on-1 Flutter and Backend performance optimization consultation.",
                "price": 95.0,
                "pricingType": PricingType.HOURLY,
                "providerId": provider.id,
                "status": ServiceStatus.PUBLISHED,
                "category": "Tech & Software",
                "images": ["https://images.unsplash.com/photo-1531403009284-440f080d1e12"],
            }
        )
        print(f"[OK] Created 2 Demo Services for Provider")

        # ------------------------------------------------------------------
        # 5. Create Orders for Dispute Scenarios
        # ------------------------------------------------------------------
        order_1 = await db.order.create(
            data={
                "userId": buyer.id,
                "productId": product_1.id,
                "status": OrderStatus.DELIVERED,
                "subTotal": 280.0,
                "platformFee": 14.0,
                "protectionFee": 5.0,
                "escrowFee": 3.0,
                "deliveryFee": 10.0,
                "totalAmount": 312.0,
                "paymentMethod": PaymentMethod.STRIPE,
                "paymentStatus": PaymentStatus.HELD_IN_ESCROW,
                "isEscrow": True,
                "hasProtection": True,
                "deliveryAddress": "123 Main Street, Apt 4B",
                "deliveryCity": "New York",
                "recipientName": "Karim Buyer",
                "recipientPhone": "+15551234567",
            }
        )

        order_2 = await db.order.create(
            data={
                "userId": buyer.id,
                "productId": product_2.id,
                "status": OrderStatus.ACCEPTED,
                "subTotal": 150.0,
                "platformFee": 7.5,
                "protectionFee": 5.0,
                "deliveryFee": 15.0,
                "totalAmount": 177.5,
                "paymentMethod": PaymentMethod.STRIPE,
                "paymentStatus": PaymentStatus.HELD_IN_ESCROW,
                "isEscrow": True,
                "hasProtection": True,
                "deliveryAddress": "742 Evergreen Terrace",
                "deliveryCity": "Springfield",
                "recipientName": "Karim Buyer",
            }
        )

        order_3 = await db.order.create(
            data={
                "userId": buyer.id,
                "productId": product_3.id,
                "status": OrderStatus.DELIVERED,
                "subTotal": 600.0,
                "platformFee": 30.0,
                "protectionFee": 10.0,
                "deliveryFee": 12.0,
                "totalAmount": 652.0,
                "paymentMethod": PaymentMethod.STRIPE,
                "paymentStatus": PaymentStatus.REFUNDED,
                "isEscrow": True,
                "hasProtection": True,
                "deliveryAddress": "456 Elm St",
                "deliveryCity": "Boston",
                "recipientName": "Karim Buyer",
            }
        )
        print(f"[OK] Created 3 Demo Orders for Buyer & Seller")

        # ------------------------------------------------------------------
        # 6. Create Service Applications for Dispute Scenarios
        # ------------------------------------------------------------------
        service_app_1 = await db.serviceapplication.create(
            data={
                "clientId": client.id,
                "serviceId": service_1.id,
                "proposedRate": 120.0,
                "expectedStartDate": "2026-09-01T10:00:00Z",
                "coverLetter": "Need immediate repair for our living room AC unit that stopped blowing cool air.",
                "status": ApplicationStatus.ACCEPTED,
                "subTotal": 120.0,
                "platformFee": 6.0,
                "protectionFee": 3.0,
                "totalAmount": 129.0,
                "paymentMethod": PaymentMethod.STRIPE,
                "paymentStatus": PaymentStatus.HELD_IN_ESCROW,
                "isEscrow": True,
                "hasProtection": True,
            }
        )

        service_app_2 = await db.serviceapplication.create(
            data={
                "clientId": client.id,
                "serviceId": service_2.id,
                "proposedRate": 95.0,
                "expectedStartDate": "2026-09-02T14:00:00Z",
                "coverLetter": "Code review consultation for Flutter architecture and state management.",
                "status": ApplicationStatus.ACCEPTED,
                "subTotal": 95.0,
                "platformFee": 4.75,
                "totalAmount": 99.75,
                "paymentMethod": PaymentMethod.STRIPE,
                "paymentStatus": PaymentStatus.PAID,
                "isEscrow": False,
            }
        )
        print(f"[OK] Created 2 Demo Service Applications for Client & Provider")

        # ------------------------------------------------------------------
        # 7. Seed Disputes
        # ------------------------------------------------------------------
        print("\n[+] Seeding Diverse Disputes...")

        disputes_data = [
            # Dispute 1: Order - Item not as described (Status: OPEN)
            {
                "disputeType": DisputeType.ORDER,
                "reason": DisputeReason.ITEM_NOT_AS_DESCRIBED,
                "description": (
                    "The headphones received have visible scratches and heavy scuffs on the left ear cup. "
                    "The seller listed the condition as 'Brand New', but this is clearly a used item."
                ),
                "evidenceImages": [
                    "https://images.unsplash.com/photo-1505740420928-5e560c06d30e",
                    "https://images.unsplash.com/photo-1484704849700-f032a568e944",
                ],
                "status": DisputeStatus.OPEN,
                "adminNotes": None,
                "orderId": order_1.id,
                "serviceApplicationId": None,
                "initiatorId": buyer.id,
                "respondentId": seller.id,
            },
            # Dispute 2: Order - Item not received (Status: UNDER_REVIEW)
            {
                "disputeType": DisputeType.ORDER,
                "reason": DisputeReason.ITEM_NOT_RECEIVED,
                "description": (
                    "The tracking status shows 'Delivered' 3 days ago, but the package was never received "
                    "at my front door or mailbox. The seller has not responded to my direct chat inquiries."
                ),
                "evidenceImages": [
                    "https://images.unsplash.com/photo-1549465220-1a8b9238cd48",
                ],
                "status": DisputeStatus.UNDER_REVIEW,
                "adminNotes": "Checking carrier delivery timestamp and GPS dropoff coordinates with courier.",
                "orderId": order_2.id,
                "serviceApplicationId": None,
                "initiatorId": buyer.id,
                "respondentId": seller.id,
            },
            # Dispute 3: Service - Service not rendered (Status: OPEN)
            {
                "disputeType": DisputeType.SERVICE,
                "reason": DisputeReason.SERVICE_NOT_RENDERED,
                "description": (
                    "The service provider failed to show up at the scheduled appointment time. "
                    "I waited for over 2 hours at the residence without receiving any prior cancellation notice."
                ),
                "evidenceImages": [],
                "status": DisputeStatus.OPEN,
                "adminNotes": None,
                "orderId": None,
                "serviceApplicationId": service_app_1.id,
                "initiatorId": client.id,
                "respondentId": provider.id,
            },
            # Dispute 4: Service - Poor service quality (Status: UNDER_REVIEW)
            {
                "disputeType": DisputeType.SERVICE,
                "reason": DisputeReason.POOR_SERVICE_QUALITY,
                "description": (
                    "The consultation session was terminated after only 15 minutes by the provider instead of the "
                    "agreed 1 hour. Incomplete guidance was provided for the requested architectural topics."
                ),
                "evidenceImages": [
                    "https://images.unsplash.com/photo-1531403009284-440f080d1e12",
                ],
                "status": DisputeStatus.UNDER_REVIEW,
                "adminNotes": "Reviewing chat conversation logs and session duration timestamps between client and provider.",
                "orderId": None,
                "serviceApplicationId": service_app_2.id,
                "initiatorId": client.id,
                "respondentId": provider.id,
            },
            # Dispute 5: Order - Resolved with Buyer Refund (Status: RESOLVED_BUYER_REFUNDED)
            {
                "disputeType": DisputeType.ORDER,
                "reason": DisputeReason.ITEM_NOT_AS_DESCRIBED,
                "description": (
                    "iPad screen had dead pixels and defective touch digitizer upon unboxing."
                ),
                "evidenceImages": [
                    "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0",
                ],
                "status": DisputeStatus.RESOLVED_BUYER_REFUNDED,
                "adminNotes": "Photographic proof validated. Full refund of $652.00 processed to buyer's original payment method.",
                "orderId": order_3.id,
                "serviceApplicationId": None,
                "initiatorId": buyer.id,
                "respondentId": seller.id,
            },
            # Dispute 6: Service - Resolved with Seller/Provider Paid (Status: RESOLVED_SELLER_PAID)
            {
                "disputeType": DisputeType.SERVICE,
                "reason": DisputeReason.OTHER,
                "description": (
                    "Client requested additional scope items outside the agreed consultation specifications."
                ),
                "evidenceImages": [],
                "status": DisputeStatus.RESOLVED_SELLER_PAID,
                "adminNotes": "Contract deliverables were fully satisfied according to initial terms. Escrow payout released to provider.",
                "orderId": None,
                "serviceApplicationId": service_app_1.id,
                "initiatorId": client.id,
                "respondentId": provider.id,
            },
            # Dispute 7: Order - Rejected (Status: REJECTED)
            {
                "disputeType": DisputeType.ORDER,
                "reason": DisputeReason.UNAUTHORIZED_CHARGE,
                "description": (
                    "Buyer claimed transaction was unauthorized."
                ),
                "evidenceImages": [],
                "status": DisputeStatus.REJECTED,
                "adminNotes": "Account 2FA authentication and device IP match confirmed buyer authorized the purchase. Dispute rejected.",
                "orderId": order_1.id,
                "serviceApplicationId": None,
                "initiatorId": buyer.id,
                "respondentId": seller.id,
            },
        ]

        created_count = 0
        for data in disputes_data:
            dispute = await db.dispute.create(data=data)
            created_count += 1
            print(f"  [+] Dispute #{dispute.id} ({dispute.disputeType} - {dispute.status}) created")

        print(f"\n[OK] Successfully created {created_count} demo disputes!")

        print("\n=======================================================")
        print("  DISPUTE SEED DATA READY FOR TESTING")
        print("=======================================================")
        print("  1. Admin Endpoint : GET /admin/disputes")
        print("     - View all disputes with status & type filtering")
        print("     - Detailed view: GET /admin/disputes/{id}")
        print("     - Resolve action: PATCH /admin/disputes/{id}/resolve")
        print("  2. User Endpoint  : GET /disputes/my")
        print("     - Login as buyer@test.com (Password123!) -> Sees buyer disputes")
        print("     - Login as seller@test.com (Password123!) -> Sees seller disputes")
        print("     - Login as client@test.com (Password123!) -> Sees client service disputes")
        print("     - Login as provider@test.com (Password123!) -> Sees provider disputes")
        print("=======================================================\n")

    except Exception as e:
        print(f"[ERROR] Failed to seed disputes: {e}", file=sys.stderr)
        raise e
    finally:
        await disconnect_db()


if __name__ == "__main__":
    asyncio.run(seed_disputes())
