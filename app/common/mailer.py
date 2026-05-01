import random
import string
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from app.core.config import get_settings

settings = get_settings()

conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

async def send_otp_email(email: str, otp: str):
    message = MessageSchema(
        subject="Your OTP for Jorden App",
        recipients=[email],
        body=f"Your OTP code is: {otp}. It is valid for 10 minutes.",
        subtype=MessageType.plain
    )
    fm = FastMail(conf)
    await fm.send_message(message)

def generate_otp(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))
