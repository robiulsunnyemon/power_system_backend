import asyncio
import os
import sys

# Add backend root directory to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.seed_admin import seed_admin
from scripts.seed_demo_stripe_data import seed_data as seed_demo_data
from scripts.seed_disputes import seed_disputes


async def main():
    print("\n=======================================================")
    print("           STARTING COMPLETE DATABASE SEED             ")
    print("=======================================================\n")
    
    print("[STEP 1/3] Seeding Admin User...")
    await seed_admin("admin@jordencuz.com", "AdminPassword123!", "System Admin")

    print("\n[STEP 2/3] Seeding Demo Products & Services...")
    await seed_demo_data()

    print("\n[STEP 3/3] Seeding Disputes Data...")
    await seed_disputes()

    print("\n=======================================================")
    print("       ALL SEED DATA GENERATION COMPLETED! 🎉          ")
    print("=======================================================\n")


if __name__ == "__main__":
    asyncio.run(main())
