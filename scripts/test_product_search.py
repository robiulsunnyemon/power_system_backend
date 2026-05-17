import asyncio
import sys
import os

# Add the project root to sys.path to allow importing from the 'app' package
sys.path.append(r"d:\robiulsunyemon\Jorden")

from app.core.db import db, connect_db, disconnect_db
from app.modules.products.service import search_products
from prisma.enums import Role, ProductCondition, ProductStatus

async def run_verification():
    try:
        await connect_db()
        print("Connected to database.")

        # 1. Setup seed data for testing
        print("\n--- Setup test products ---")
        
        # Find or create a seller
        sellers = await db.user.find_many(where={"roles": {"has": Role.SELLER}})
        if not sellers:
            # Try to find user and update roles
            users = await db.user.find_many()
            if not users:
                print("Test aborted: No users in DB.")
                return
            seller = users[0]
            await db.user.update(
                where={"id": seller.id},
                data={"roles": {"set": [Role.USER, Role.SELLER]}}
            )
            print(f"Updated User {seller.fullname} to have SELLER role.")
        else:
            seller = sellers[0]

        # Find or create categories
        categories = await db.category.find_many()
        if len(categories) < 2:
            cat1 = await db.category.upsert(
                where={"name": "ELECTRONICS"},
                data={"create": {"name": "ELECTRONICS"}, "update": {}}
            )
            cat2 = await db.category.upsert(
                where={"name": "FASHION"},
                data={"create": {"name": "FASHION"}, "update": {}}
            )
        else:
            cat1 = categories[0]
            cat2 = categories[1]
        
        print(f"Using Categories: '{cat1.name}' (ID: {cat1.id}) and '{cat2.name}' (ID: {cat2.id})")

        # Let's clean up any previous test products
        await db.product.delete_many(where={"title": {"startswith": "[TEST-SEARCH]"}})

        # Create test products
        p1 = await db.product.create(
            data={
                "title": "[TEST-SEARCH] Premium Wireless Bluetooth Headphone",
                "description": "High fidelity audio with noise cancelling capability.",
                "price": 150.0,
                "total_fee": 150.0,
                "condition": ProductCondition.NEW,
                "status": ProductStatus.ACTIVE,
                "sellerId": seller.id,
                "categoryId": cat1.id
            }
        )

        p2 = await db.product.create(
            data={
                "title": "[TEST-SEARCH] Vintage Leather Jacket",
                "description": "Genuine brown leather jacket for winter wear. stylish look.",
                "price": 200.0,
                "total_fee": 200.0,
                "condition": ProductCondition.NEW,
                "status": ProductStatus.ACTIVE,
                "sellerId": seller.id,
                "categoryId": cat2.id
            }
        )

        p3 = await db.product.create(
            data={
                "title": "[TEST-SEARCH] Ergonomic Office Desk",
                "description": "Wooden desk suitable for home office or study. modern design.",
                "price": 120.0,
                "total_fee": 120.0,
                "condition": ProductCondition.NEW,
                "status": ProductStatus.ACTIVE,
                "sellerId": seller.id,
                "categoryId": cat1.id # Same category as headphones for category check
            }
        )

        print("Test products successfully created.")

        # 2. Test scenario 1: Empty search query (should return active products)
        print("\n--- Test Scenario 1: Empty Search Query ---")
        res1 = await search_products()
        print(f"SUCCESS: Returned {len(res1['products'])} active products (Total: {res1['total']})")

        # 3. Test scenario 2: Single word search matching title
        print("\n--- Test Scenario 2: Search matching title (case-insensitive) ---")
        res2 = await search_products(query_str="wireless")
        matching_titles = [p["title"] for p in res2["products"]]
        print(f"Search Query: 'wireless' -> Matches: {matching_titles}")
        if len(res2["products"]) >= 1 and "[TEST-SEARCH] Premium Wireless Bluetooth Headphone" in matching_titles:
            print("SUCCESS: Perfectly matched title.")
        else:
            print("FAILED: Did not match correctly.")

        # 4. Test scenario 3: Single word search matching description
        print("\n--- Test Scenario 3: Search matching description (case-insensitive) ---")
        res3 = await search_products(query_str="cancelling")
        matching_titles = [p["title"] for p in res3["products"]]
        print(f"Search Query: 'cancelling' -> Matches: {matching_titles}")
        if len(res3["products"]) >= 1 and "[TEST-SEARCH] Premium Wireless Bluetooth Headphone" in matching_titles:
            print("SUCCESS: Perfectly matched description.")
        else:
            print("FAILED: Did not match correctly.")

        # 5. Test scenario 4: Multi-word search matching ANY word (e.g. 'jacket office')
        print("\n--- Test Scenario 4: Multi-word search (matches ANY word) ---")
        res4 = await search_products(query_str="jacket office")
        matching_titles = [p["title"] for p in res4["products"]]
        print(f"Search Query: 'jacket office' -> Matches: {matching_titles}")
        # Should match both vintage leather jacket and ergonomic office desk
        if len(res4["products"]) >= 2:
            print("SUCCESS: Successfully matched ANY word in query across title and description.")
        else:
            print("FAILED: Did not match multiple products.")

        # 6. Test scenario 5: Search with query + category_id filter
        print("\n--- Test Scenario 5: Search query with Category ID filter ---")
        # Search for "desk" with Category 1 (cat1) -> should match p3
        res5 = await search_products(query_str="desk", category_id=cat1.id)
        matching_titles_5 = [p["title"] for p in res5["products"]]
        print(f"Search Query: 'desk', Category ID: {cat1.id} -> Matches: {matching_titles_5}")
        if len(res5["products"]) == 1 and p3.title in matching_titles_5:
            print("SUCCESS: Correctly matched query + category filter.")
        else:
            print("FAILED: Category filter failed.")

        # Search for "desk" with Category 2 (cat2) -> should NOT match anything (p3 is in cat1)
        res6 = await search_products(query_str="desk", category_id=cat2.id)
        print(f"Search Query: 'desk', Category ID: {cat2.id} -> Matches: {[p['title'] for p in res6['products']]}")
        if len(res6["products"]) == 0:
            print("SUCCESS: Category exclusion filter successfully worked.")
        else:
            print("FAILED: Category exclusion filter did not work.")

        # 7. Cleanup test data
        print("\n--- Cleanup ---")
        await db.product.delete_many(where={"title": {"startswith": "[TEST-SEARCH]"}})
        print("SUCCESS: Cleanup completed successfully.")

    except Exception as e:
        print(f"Exception in search test script: {e}")
    finally:
        await disconnect_db()

if __name__ == "__main__":
    asyncio.run(run_verification())
