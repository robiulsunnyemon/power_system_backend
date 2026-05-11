from datetime import timedelta
from fastapi import HTTPException, status, BackgroundTasks
from app.core.db import db
from app.common.security import hash_password, verify_password, create_access_token
from app.common.mailer import generate_otp, send_otp_email
from app.modules.auth.schemas import SignupRequest, LoginRequest, VerifyOTPRequest
from prisma.enums import AccountStatus

async def signup_user(data: SignupRequest, background_tasks: BackgroundTasks):
    if data.password != data.confirm_password:
        raise HTTPException(status_code=422, detail="password and confirm password does not match")

    user = await db.user.find_unique(where={"email": data.email})
    if user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    otp = generate_otp()
    hashed_pwd = hash_password(data.password)
    
    await db.user.create(
        data={
            "fullname": data.fullname,
            "email": data.email,
            "password": hashed_pwd,
            "isAgreed": data.isAgreed,
            "roles": [r.value for r in data.roles],
            "otp": otp,
            "isVerified": False,
            "accountStatus": AccountStatus.PENDING
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
    
    last_active_role = user.lastActiveRole
    
    if data.role:
        if data.role.value not in user.roles:
            raise HTTPException(status_code=400, detail=f"User does not have the role: {data.role.value}")
        
        last_active_role = data.role.value
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
