import asyncio
import sys
import os
import random

# Add the project root to sys.path to allow importing from the 'app' package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.db import db, connect_db, disconnect_db
from prisma.enums import Role, ProductCondition, ProductStatus

async def seed_products():
    """
    Creates 10 products assigned to existing sellers.
    """
    try:
        await connect_db()
        
        # 1. Find existing sellers
        sellers = await db.user.find_many(where={"roles": {"has": Role.SELLER}})
        if not sellers:
            print("[!] No sellers found. Please run seller_seed.py first.")
            return

        # 2. Get or create categories
        categories = ["ELECTRONICS", "FURNITURE", "CLOTHING", "SPORTS", "BOOKS"]
        category_ids = []
        for cat_name in categories:
            cat = await db.category.upsert(
                where={"name": cat_name},
                data={"create": {"name": cat_name}, "update": {}}
            )
            category_ids.append(cat.id)

        # 3. Create 10 products
        created_count = 0
        product_titles = [
            "Ultra HD 4K TV", "Ergonomic Office Chair", "Cotton T-Shirt", 
            "Professional Camera", "Wireless Headphones", "Mountain Bike",
            "Gaming Laptop", "Modern Sofa", "Running Shoes", "Bestseller Novel"
        ]

        for i in range(10):
            seller = random.choice(sellers)
            cat_id = random.choice(category_ids)
            title = product_titles[i]
            price = random.uniform(20.0, 1500.0)
            
            await db.product.create(
                data={
                    "title": title,
                    "description": f"This is a high-quality {title.lower()} for testing purposes.",
                    "price": price,
                    "tax_fee": price * 0.1,
                    "delivery_fee": 5.0,
                    "total_fee": price * 1.1 + 5.0,
                    "condition": random.choice(list(ProductCondition)),
                    "status": ProductStatus.ACTIVE,
                    "images": [f"https://picsum.photos/seed/product{i}/800/600"],
                    "sellerId": seller.id,
                    "categoryId": cat_id
                }
            )
            created_count += 1
            print(f"[+] Created Product: {title} (Seller: {seller.email})")

        print(f"\n[!] Finished! Total products created: {created_count}")
            
    except Exception as e:
        print(f"[!] Error seeding products: {e}")
    finally:
        await disconnect_db()

if __name__ == "__main__":
    asyncio.run(seed_products())
