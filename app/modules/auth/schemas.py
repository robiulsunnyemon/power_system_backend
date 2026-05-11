from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from enum import Enum

class Role(str, Enum):
    USER = "USER"
    SELLER = "SELLER"
    SERVICE_PROVIDER = "SERVICE_PROVIDER"

class SignupRequest(BaseModel):
    fullname: str
    email: EmailStr
    password: str = Field(..., min_length=6)
    confirm_password: str
    isAgreed: bool
    roles: List[Role] = [Role.USER]


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    role: Optional[Role] = None

class ForgetPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
