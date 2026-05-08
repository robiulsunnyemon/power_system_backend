import asyncio
import sys
import os
import random
import json

# Add the project root to sys.path to allow importing from the 'app' package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.db import db, connect_db, disconnect_db
from prisma.enums import Role, ServiceStatus, PricingType

async def seed_services():
    """
    Creates 15 services assigned to existing service providers.
    """
    try:
        await connect_db()
        
        # 1. Find existing service providers
        providers = await db.user.find_many(where={"roles": {"has": Role.SERVICE_PROVIDER}})
        if not providers:
            print("[!] No service providers found. Please run service_provider_seed.py first.")
            return

        # 2. Create 15 services
        created_count = 0
        service_titles = [
            "House Cleaning", "Plumbing Repair", "Electrical Work", "Graphic Design",
            "Content Writing", "Web Development", "Yoga Instruction", "Tutor (Math)",
            "Personal Training", "Lawnt Care", "Pet Grooming", "Photography",
            "Video Editing", "Social Media Management", "Consulting"
        ]

        categories = ["CLEANING", "MAINTENANCE", "CREATIVE", "TEACHING", "HEALTH", "TECH"]

        for i in range(15):
            provider = random.choice(providers)
            title = service_titles[i]
            category = random.choice(categories)
            price = random.uniform(50.0, 500.0)
            
            await db.service.create(
                data={
                    "title": title,
                    "description": f"Professional {title.lower()} service by an expert.",
                    "price": price,
                    "pricingType": random.choice(list(PricingType)),
                    "category": category,
                    "status": ServiceStatus.PUBLISHED,
                    "images": [f"https://picsum.photos/seed/service{i}/800/600"],
                    "providerId": provider.id,
                    "availability": json.dumps(["M", "W", "F"]),
                    "requirements": json.dumps([
                        {"title": "Space", "description": "Needs 10x10 area"},
                        {"title": "Power", "description": "Needs 220V outlet"}
                    ])
                }
            )
            created_count += 1
            print(f"[+] Created Service: {title} (Provider: {provider.email})")

        print(f"\n[!] Finished! Total services created: {created_count}")
            
    except Exception as e:
        print(f"[!] Error seeding services: {e}")
    finally:
        await disconnect_db()

if __name__ == "__main__":
    asyncio.run(seed_services())
