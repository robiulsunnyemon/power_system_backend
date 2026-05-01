from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from app.modules.auth.schemas import SignupRequest, LoginRequest, VerifyOTPRequest, ForgetPasswordRequest, ResetPasswordRequest
from app.modules.auth import service
from app.common.security import decode_token

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/signup")
async def signup(data: SignupRequest, background_tasks: BackgroundTasks):
    return await service.signup_user(data, background_tasks)

@router.post("/verify-otp")
async def verify_otp(data: VerifyOTPRequest):
    return await service.verify_otp(data)

@router.post("/resend-otp")
async def resend_otp(email: str, background_tasks: BackgroundTasks):
    return await service.resend_otp(email, background_tasks)

@router.post("/login")
async def login(data: LoginRequest):
    return await service.login_user(data)

@router.post("/forget-password")
async def forget_password(data: ForgetPasswordRequest, background_tasks: BackgroundTasks):
    return await service.forget_password(data.email, background_tasks)

@router.post("/verify-forget-otp")
async def verify_forget_otp(email: str, otp: str):
    return await service.verify_forget_otp(email, otp)

@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest):
    payload = decode_token(data.token)
    if not payload or payload.get("purpose") != "reset_password":
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    
    user_id = int(payload.get("sub"))
    return await service.reset_password(user_id, data.new_password)
