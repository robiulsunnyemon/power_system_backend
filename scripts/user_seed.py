import asyncio
import sys
import os
from datetime import datetime, timedelta
import random

# Add the project root to sys.path to allow importing from the 'app' package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.db import db, connect_db, disconnect_db
from app.common.security import hash_password
from prisma.enums import Role, AccountStatus

async def seed_users():
    """
    Creates a variety of users with different createdAt dates to test dashboard filters.
    """
    try:
        await connect_db()
        
        password = "123456"
        hashed_pwd = hash_password(password)
        
        # Helper to create user if not exists
        async def create_test_user(email, fullname, status, created_at):
            user = await db.user.find_unique(where={"email": email})
            if not user:
                await db.user.create(
                    data={
                        "fullname": fullname,
                        "email": email,
                        "password": hashed_pwd,
                        "roles": [Role.USER],
                        "isVerified": True,
                        "accountStatus": status,
                        "isAgreed": True,
                        "createdAt": created_at
                    }
                )
                return True
            return False

        created_count = 0
        now = datetime.now()

        print("Seeding users for Weekly/Monthly tests...")
        # 1. Last 7 days (5 users)
        for i in range(5):
            days_ago = random.randint(0, 6)
            created_at = now - timedelta(days=days_ago, hours=random.randint(0, 23))
            if await create_test_user(f"user{i}@test.com", f"Week User {i}", AccountStatus.ACTIVE, created_at):
                created_count += 1

        # 2. Last 30 days (10 users)
        for i in range(10):
            days_ago = random.randint(7, 29)
            created_at = now - timedelta(days=days_ago)
            status = AccountStatus.ACTIVE if i % 2 == 0 else AccountStatus.PENDING
            if await create_test_user(f"user{i}@test.com", f"Month User {i}", status, created_at):
                created_count += 1

        print("Seeding users for 6-Month/Yearly tests...")
        # 3. Last 6 months (15 users)
        for i in range(15):
            days_ago = random.randint(30, 180)
            created_at = now - timedelta(days=days_ago)
            if await create_test_user(f"user{i}@test.com", f"6-Month User {i}", AccountStatus.ACTIVE, created_at):
                created_count += 1

        # 4. Last 12 months (20 users)
        for i in range(20):
            days_ago = random.randint(180, 365)
            created_at = now - timedelta(days=days_ago)
            status = AccountStatus.ACTIVE if i % 3 != 0 else AccountStatus.PENDING
            if await create_test_user(f"user{i}@test.com", f"Year User {i}", status, created_at):
                created_count += 1

        print("Seeding users for Year Range test...")
        # 5. Last 3 years (15 users)
        for i in range(15):
            days_ago = random.randint(366, 365 * 3)
            created_at = now - timedelta(days=days_ago)
            if await create_test_user(f"user{i}@test.com", f"Old User {i}", AccountStatus.ACTIVE, created_at):
                created_count += 1

        print(f"\n[!] Finished! Total new users created: {created_count}")
        print(f"    Default Password for all: {password}")
            
    except Exception as e:
        print(f"[!] Error seeding users: {e}")
    finally:
        await disconnect_db()

if __name__ == "__main__":
    asyncio.run(seed_users())
