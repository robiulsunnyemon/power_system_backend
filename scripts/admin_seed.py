import asyncio
import sys
import os

# Add the project root to sys.path to allow importing from the 'app' package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.db import db, connect_db, disconnect_db
from app.common.security import hash_password
from prisma.enums import Role, AccountStatus

async def seed_admin():
    """
    Creates an initial admin user in the database.
    """
    try:
        await connect_db()
        
        email = "admin@powersystem.com"
        password = "123456"
        
        # Check if user already exists
        user = await db.user.find_unique(where={"email": email})
        
        if user:
            print(f"[-] Admin with email {email} already exists.")
        else:
            hashed_pwd = hash_password(password)
            await db.user.create(
                data={
                    "fullname": "Admin User",
                    "email": email,
                    "password": hashed_pwd,
                    "role": Role.ADMIN,
                    "isVerified": True,
                    "accountStatus": AccountStatus.ACTIVE,
                    "isAgreed": True
                }
            )
            print(f"[+] Admin user created successfully!")
            print(f"    Email: {email}")
            print(f"    Password: {password}")
            
    except Exception as e:
        print(f"[!] Error seeding admin: {e}")
    finally:
        await disconnect_db()

if __name__ == "__main__":
    asyncio.run(seed_admin())
