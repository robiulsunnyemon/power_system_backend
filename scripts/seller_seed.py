import asyncio
import sys
import os

# Add the project root to sys.path to allow importing from the 'app' package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.db import db, connect_db, disconnect_db
from app.common.security import hash_password
from prisma.enums import Role, AccountStatus

async def seed_sellers():
    """
    Creates 10 seller accounts in the database for testing.
    """
    try:
        await connect_db()
        
        password = "123456"
        hashed_pwd = hash_password(password)
        
        created_count = 0
        for i in range(1, 11):
            email = f"seller{i}@powersystem.com"
            fullname = f"Seller {i}"
            
            # Check if user already exists
            user = await db.user.find_unique(where={"email": email})
            
            if user:
                print(f"[-] Seller with email {email} already exists.")
            else:
                await db.user.create(
                    data={
                        "fullname": fullname,
                        "email": email,
                        "password": hashed_pwd,
                        "role": Role.SELLER,
                        "isVerified": True,
                        "accountStatus": AccountStatus.ACTIVE,
                        "isAgreed": True
                    }
                )
                created_count += 1
                print(f"[+] Created: {email}")
        
        print(f"\n[!] Finished! Total sellers created: {created_count}")
        print(f"    Default Password for all: {password}")
            
    except Exception as e:
        print(f"[!] Error seeding sellers: {e}")
    finally:
        await disconnect_db()

if __name__ == "__main__":
    asyncio.run(seed_sellers())
