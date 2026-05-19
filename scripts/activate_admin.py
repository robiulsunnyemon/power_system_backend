import asyncio
import sys
import os

# Add the project root to sys.path to allow importing from the 'app' package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.db import db, connect_db, disconnect_db
from prisma.enums import Role, AccountStatus

async def activate_admin():
    """
    Updates the admin user's account status to ACTIVE in the database.
    """
    try:
        await connect_db()
        
        email = "admin@powersystem.com"
        
        # Check if user already exists
        user = await db.user.find_unique(where={"email": email})
        
        if user:
            if user.accountStatus == AccountStatus.ACTIVE:
                print(f"[-] Admin with email {email} is already ACTIVE.")
            else:
                await db.user.update(
                    where={"email": email},
                    data={
                        "accountStatus": AccountStatus.ACTIVE
                    }
                )
                print(f"[+] Admin user ({email}) account status updated to ACTIVE successfully!")
        else:
            print(f"[-] Admin with email {email} not found. Please run admin_seed.py first.")
            
    except Exception as e:
        print(f"[!] Error activating admin: {e}")
    finally:
        await disconnect_db()

if __name__ == "__main__":
    asyncio.run(activate_admin())
