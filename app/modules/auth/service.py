from datetime import timedelta
from fastapi import HTTPException, status, BackgroundTasks
from app.core.db import db
from app.common.security import hash_password, verify_password, create_access_token
from app.common.mailer import generate_otp, send_otp_email
from app.modules.auth.schemas import SignupRequest, LoginRequest, VerifyOTPRequest, ChangePasswordRequest, GoogleLoginRequest, AppleLoginRequest
from app.common.social_auth import verify_google_token, verify_apple_token
from prisma.enums import AccountStatus

async def signup_user(data: SignupRequest, background_tasks: BackgroundTasks):
    if data.password != data.confirm_password:
        raise HTTPException(status_code=422, detail="password and confirm password does not match")

    user = await db.user.find_unique(where={"email": data.email})
    if user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    otp = generate_otp()
    hashed_pwd = hash_password(data.password)
    
    roles = [r.value for r in data.roles]
    # Set lastActiveRole to the role if only one is provided, otherwise default to USER
    last_active_role = roles[0] if len(roles) == 1 else "USER"
    
    await db.user.create(
        data={
            "fullname": data.fullname,
            "email": data.email,
            "password": hashed_pwd,
            "isAgreed": data.isAgreed,
            "roles": roles,
            "lastActiveRole": last_active_role,
            "otp": otp,
            "isVerified": False,
            "accountStatus": AccountStatus.PENDING,
            "notificationSettings": {
                "create": {
                    "orderUpdates": True,
                    "serviceUpdates": True,
                    "newServiceAlerts": True,
                    "messageNotifications": True
                }
            }
        }
    )
    
    # Send OTP in Background
    background_tasks.add_task(send_otp_email, data.email, otp)
    
    return {"message": "Signup successful. Please verify your OTP."}

async def verify_otp(data: VerifyOTPRequest):
    user = await db.user.find_unique(where={"email": data.email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.otp != data.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")
    
    await db.user.update(
        where={"id": user.id},
        data={
            "isVerified": True,
            "accountStatus": AccountStatus.ACTIVE,
            "otp": None
        }
    )
    
    return {"message": "Email verified successfully. You can now login."}

async def resend_otp(email: str, background_tasks: BackgroundTasks):
    user = await db.user.find_unique(where={"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    otp = generate_otp()
    await db.user.update(
        where={"id": user.id},
        data={"otp": otp}
    )
    
    background_tasks.add_task(send_otp_email, email, otp)
    return {"message": "OTP resent successfully."}

async def login_user(data: LoginRequest):
    user = await db.user.find_unique(where={"email": data.email})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not verify_password(data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not user.isVerified:
        raise HTTPException(status_code=403, detail="Email not verified")
    
    if user.accountStatus != AccountStatus.ACTIVE:
        raise HTTPException(status_code=403, detail=f"Account is {user.accountStatus}")
    
    # Check maintenance mode
    from app.modules.settings.service import is_maintenance_mode_active
    if await is_maintenance_mode_active() and "ADMIN" not in user.roles:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="System is in maintenance mode. Only admins are allowed to login."
        )
    
    last_active_role = user.lastActiveRole
    
    if data.role:
        if data.role.value not in user.roles:
            raise HTTPException(status_code=400, detail=f"User does not have the role: {data.role.value}")
        
        last_active_role = data.role.value
        await db.user.update(
            where={"id": user.id},
            data={"lastActiveRole": last_active_role}
        )
    elif len(user.roles) == 1 and last_active_role != user.roles[0]:
        # Auto-fix lastActiveRole if the user has only one role and it's not currently active
        last_active_role = user.roles[0]
        await db.user.update(
            where={"id": user.id},
            data={"lastActiveRole": last_active_role}
        )
    
    token = create_access_token(data={
        "sub": str(user.id), 
        "email": user.email, 
        "roles": user.roles, 
        "token_version": user.tokenVersion,
        "last_active_role": last_active_role
    })

    return {
        "access_token": token, 
        "token_type": "bearer",
        "last_active_role": last_active_role
    }

async def forget_password(email: str, background_tasks: BackgroundTasks):
    user = await db.user.find_unique(where={"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    otp = generate_otp()
    await db.user.update(
        where={"id": user.id},
        data={"otp": otp}
    )
    
    background_tasks.add_task(send_otp_email, email, otp)
    return {"message": "Password reset OTP sent."}

async def verify_forget_otp(email: str, otp: str):
    user = await db.user.find_unique(where={"email": email})
    if not user or user.otp != otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")
    
    # Create a temporary token for reset
    reset_token = create_access_token(data={"sub": str(user.id), "purpose": "reset_password"}, expires_delta=timedelta(minutes=10))
    
    await db.user.update(
        where={"id": user.id},
        data={"otp": None}
    )
    
    return {"reset_token": reset_token}

async def reset_password(user_id: int, new_password: str):
    hashed_pwd = hash_password(new_password)
    await db.user.update(
        where={"id": user_id},
        data={"password": hashed_pwd}
    )
    return {"message": "Password reset successful."}

async def change_password(user_id: int, data: ChangePasswordRequest):
    user = await db.user.find_unique(where={"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if not verify_password(data.current_password, user.password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
        
    if data.new_password != data.confirm_password:
        raise HTTPException(status_code=422, detail="New password and confirm password do not match")
        
    hashed_pwd = hash_password(data.new_password)
    await db.user.update(
        where={"id": user_id},
        data={"password": hashed_pwd}
    )
    return {"message": "Password changed successfully"}

async def login_with_google(data: GoogleLoginRequest):
    # 1. Verify Google token
    payload = await verify_google_token(data.id_token)
    
    email = payload.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email not provided in Google token")
        
    google_id = payload.get("sub")
    fullname = payload.get("name") or email.split("@")[0].capitalize()
    
    # 2. Check if user already exists by googleId
    user = await db.user.find_unique(where={"googleId": google_id})
    
    if not user:
        # 3. Check if user already exists by email (Automatic Link Policy)
        user = await db.user.find_unique(where={"email": email})
        
        if user:
            # Link googleId to existing account and ensure it is active and verified
            user = await db.user.update(
                where={"id": user.id},
                data={
                    "googleId": google_id,
                    "isVerified": True,
                    "accountStatus": AccountStatus.ACTIVE
                }
            )
        else:
            # 4. Create new user
            user = await db.user.create(
                data={
                    "fullname": fullname,
                    "email": email,
                    "googleId": google_id,
                    "isAgreed": True,
                    "roles": ["USER"],
                    "lastActiveRole": "USER",
                    "isVerified": True,
                    "accountStatus": AccountStatus.ACTIVE,
                    "notificationSettings": {
                        "create": {
                            "orderUpdates": True,
                            "serviceUpdates": True,
                            "newServiceAlerts": True,
                            "messageNotifications": True
                        }
                    }
                }
            )
            
    # Ensure account is active and verified
    if user.accountStatus != AccountStatus.ACTIVE:
        raise HTTPException(status_code=403, detail=f"Account is {user.accountStatus}")
        
    # Check maintenance mode
    from app.modules.settings.service import is_maintenance_mode_active
    if await is_maintenance_mode_active() and "ADMIN" not in user.roles:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="System is in maintenance mode. Only admins are allowed to login."
        )
        
    token = create_access_token(data={
        "sub": str(user.id), 
        "email": user.email, 
        "roles": user.roles, 
        "token_version": user.tokenVersion,
        "last_active_role": user.lastActiveRole
    })

    return {
        "access_token": token, 
        "token_type": "bearer",
        "last_active_role": user.lastActiveRole
    }

async def login_with_apple(data: AppleLoginRequest):
    # 1. Verify Apple token
    payload = await verify_apple_token(data.identity_token)
    
    email = payload.get("email")
    apple_id = payload.get("sub")
    
    # If Apple relay/private email isn't provided or we need a fallback email:
    if not email:
        email = f"{apple_id}@apple.user"  # Fallback custom email
        
    # Auto-assign name from email or ID (User decided)
    fullname = email.split("@")[0].capitalize()
    if fullname.lower().startswith("apple.user") or not fullname:
        fullname = f"Apple User {apple_id[:5]}"
        
    # 2. Check if user already exists by appleId
    user = await db.user.find_unique(where={"appleId": apple_id})
    
    if not user:
        # 3. Check if user already exists by email (Automatic Link Policy)
        user = await db.user.find_unique(where={"email": email})
        
        if user:
            # Link appleId to existing account
            user = await db.user.update(
                where={"id": user.id},
                data={
                    "appleId": apple_id,
                    "isVerified": True,
                    "accountStatus": AccountStatus.ACTIVE
                }
            )
        else:
            # 4. Create new user
            user = await db.user.create(
                data={
                    "fullname": fullname,
                    "email": email,
                    "appleId": apple_id,
                    "isAgreed": True,
                    "roles": ["USER"],
                    "lastActiveRole": "USER",
                    "isVerified": True,
                    "accountStatus": AccountStatus.ACTIVE,
                    "notificationSettings": {
                        "create": {
                            "orderUpdates": True,
                            "serviceUpdates": True,
                            "newServiceAlerts": True,
                            "messageNotifications": True
                        }
                    }
                }
            )
            
    if user.accountStatus != AccountStatus.ACTIVE:
        raise HTTPException(status_code=403, detail=f"Account is {user.accountStatus}")
        
    # Check maintenance mode
    from app.modules.settings.service import is_maintenance_mode_active
    if await is_maintenance_mode_active() and "ADMIN" not in user.roles:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="System is in maintenance mode. Only admins are allowed to login."
        )
        
    token = create_access_token(data={
        "sub": str(user.id), 
        "email": user.email, 
        "roles": user.roles, 
        "token_version": user.tokenVersion,
        "last_active_role": user.lastActiveRole
    })

    return {
        "access_token": token, 
        "token_type": "bearer",
        "last_active_role": user.lastActiveRole
    }
