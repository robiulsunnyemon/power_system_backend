import asyncio
import sys
import os

# Add root directory to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, r"C:\Users\USER\anaconda3\Lib\site-packages")

from app.core.db import connect_db, disconnect_db, db
from app.common.security import hash_password
from prisma.enums import Role, AccountStatus, ProductStatus, ServiceStatus, PricingType, ItemSize, ProductCondition

async def seed_data():
    await connect_db()
    print("[+] Seeding Demo Users, Products, and Services for Stripe Testing...")
    
    hashed_pwd = hash_password("Password123!")

    # 1. Create Dummy Buyer
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
            },
            "update": {
                "password": hashed_pwd,
                "accountStatus": AccountStatus.ACTIVE,
            }
        }
    )
    print(f"[OK] Buyer created: buyer@test.com (Password: Password123!)")

    # 2. Create Dummy Seller
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
                "stripeAccountStatus": "PENDING",
            },
            "update": {
                "password": hashed_pwd,
                "accountStatus": AccountStatus.ACTIVE,
            }
        }
    )
    print(f"[OK] Seller created: seller@test.com (Password: Password123!)")

    # Ensure profile for seller
    await db.userprofile.upsert(
        where={"userId": seller.id},
        data={
            "create": {"userId": seller.id, "trust_score": 90.0, "raw_score": 450.0},
            "update": {"trust_score": 90.0}
        }
    )

    # 3. Create Dummy Service Provider
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
                "stripeAccountStatus": "PENDING",
            },
            "update": {
                "password": hashed_pwd,
                "accountStatus": AccountStatus.ACTIVE,
            }
        }
    )
    print(f"[OK] Service Provider created: provider@test.com (Password: Password123!)")

    # 4. Create Category & Products for Seller
    category = await db.category.find_first()
    if not category:
        category = await db.category.create(data={"name": "Electronics"})

    product_1 = await db.product.create(
        data={
            "title": "Wireless Noise Canceling Headphones",
            "description": "High quality bluetooth headphones with active noise cancellation.",
            "price": 100.0,
            "condition": ProductCondition.NEW,
            "sellerId": seller.id,
            "categoryId": category.id,
            "status": ProductStatus.ACTIVE,
            "itemSize": ItemSize.SMALL,
            "images": ["https://images.unsplash.com/photo-1505740420928-5e560c06d30e"]
        }
    )

    product_2 = await db.product.create(
        data={
            "title": "4K Smart LED TV 55 inch",
            "description": "Ultra HD Smart TV with HDR support.",
            "price": 450.0,
            "condition": ProductCondition.NEW,
            "sellerId": seller.id,
            "categoryId": category.id,
            "status": ProductStatus.ACTIVE,
            "itemSize": ItemSize.MEDIUM,
            "images": ["https://images.unsplash.com/photo-1593359677879-a4bb92f829d1"]
        }
    )
    print("[OK] Created 2 Demo Products for Seller")

    # 5. Create Service for Provider
    service_1 = await db.service.create(
        data={
            "title": "Home Appliance Repair & Maintenance",
            "description": "Expert repair service for refrigerators, washers, and AC units.",
            "price": 80.0,
            "pricingType": PricingType.FIXED,
            "providerId": provider.id,
            "status": ServiceStatus.PUBLISHED,
            "images": ["https://images.unsplash.com/photo-1581092160607-ee22621dd758"]
        }
    )
    print("[OK] Created Demo Service for Provider")

    await disconnect_db()
    print("[DONE] Demo data seeding complete! You can now start testing.")

if __name__ == "__main__":
    asyncio.run(seed_data())
