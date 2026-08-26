import argparse
import asyncio
import os
import sys

# Add backend root directory to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.db import connect_db, disconnect_db, db
from app.common.security import hash_password
from prisma.enums import Role, AccountStatus


async def seed_admin(email: str, password: str, fullname: str):
    """
    Seeds or updates an Admin user in the database.
    """
    await connect_db()
    print(f"\n[+] Seeding Admin User into Database...")

    hashed_pwd = hash_password(password)

    try:
        # 1. Upsert Admin User
        admin_user = await db.user.upsert(
            where={"email": email},
            data={
                "create": {
                    "fullname": fullname,
                    "email": email,
                    "password": hashed_pwd,
                    "roles": [Role.ADMIN, Role.USER],
                    "accountStatus": AccountStatus.ACTIVE,
                    "isVerified": True,
                    "isAgreed": True,
                    "lastActiveRole": Role.ADMIN,
                },
                "update": {
                    "fullname": fullname,
                    "password": hashed_pwd,
                    "roles": [Role.ADMIN, Role.USER],
                    "accountStatus": AccountStatus.ACTIVE,
                    "isVerified": True,
                    "isAgreed": True,
                },
            },
        )
        print(f"[OK] Admin User Upserted successfully!")
        print(f"     - ID: {admin_user.id}")
        print(f"     - Fullname: {admin_user.fullname}")
        print(f"     - Email: {admin_user.email}")
        print(f"     - Roles: {admin_user.roles}")
        print(f"     - Status: {admin_user.accountStatus}")

        # 2. Ensure UserProfile
        profile = await db.userprofile.upsert(
            where={"userId": admin_user.id},
            data={
                "create": {
                    "userId": admin_user.id,
                    "trust_score": 100.0,
                    "raw_score": 500.0,
                },
                "update": {
                    "trust_score": 100.0,
                    "raw_score": 500.0,
                },
            },
        )
        print(f"[OK] Admin Profile configured with trust score {profile.trust_score}")

        # 3. Ensure NotificationSetting
        notif_setting = await db.notificationsetting.upsert(
            where={"userId": admin_user.id},
            data={
                "create": {
                    "userId": admin_user.id,
                    "orderUpdates": True,
                    "serviceUpdates": True,
                    "newServiceAlerts": True,
                    "messageNotifications": True,
                },
                "update": {
                    "orderUpdates": True,
                    "serviceUpdates": True,
                    "newServiceAlerts": True,
                    "messageNotifications": True,
                },
            },
        )
        print(f"[OK] Admin Notification settings configured.")

        print("\n=======================================================")
        print("  ADMIN CREDENTIALS CREATED / UPDATED SUCCESSFULLY")
        print("=======================================================")
        print(f"  Email    : {email}")
        print(f"  Password : {password}")
        print("=======================================================\n")

    except Exception as e:
        print(f"[ERROR] Failed to seed admin user: {e}", file=sys.stderr)
        raise e
    finally:
        await disconnect_db()


def parse_args():
    parser = argparse.ArgumentParser(description="Seed an Admin user into the database.")
    parser.add_argument(
        "--email",
        type=str,
        default=os.getenv("ADMIN_EMAIL", "admin@jordencuz.com"),
        help="Admin email address (default: admin@jordencuz.com or ADMIN_EMAIL env)",
    )
    parser.add_argument(
        "--password",
        type=str,
        default=os.getenv("ADMIN_PASSWORD", "AdminPassword123!"),
        help="Admin password (default: AdminPassword123! or ADMIN_PASSWORD env)",
    )
    parser.add_argument(
        "--fullname",
        type=str,
        default=os.getenv("ADMIN_NAME", "System Admin"),
        help="Admin full name (default: System Admin or ADMIN_NAME env)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(seed_admin(email=args.email, password=args.password, fullname=args.fullname))
