from fastapi_mail import ConnectionConfig
from fastapi_mail import FastMail, MessageSchema, MessageType
from pydantic import EmailStr
from config import settings


mail_config = ConnectionConfig(
    MAIL_USERNAME=settings.mail_username,
    MAIL_PASSWORD=settings.mail_password.get_secret_value(),
    MAIL_FROM=settings.mail_from,
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
)
async def send_reset_email(to_email: EmailStr, username: str,token:str):
    message = MessageSchema(
        subject="Reset your password for Linkly Shortener",
        recipients=[to_email],
        body = f"""
            <p>Hi {username},</p>

            <p>You requested a password reset.</p>

            <p>Use the token below to reset your password:</p>

            <p><strong>{token}</strong></p>

            <p>You can use this token with the password reset endpoint in the API documentation.</p>

            <p>This token will expire in <strong>1 hour</strong>.</p>

            <p>If you didn't request a password reset, you can safely ignore this email.</p>

            <br>

            <p>
            Best regards,<br>
            Linkly
            </p>
            """,
        subtype=MessageType.html,
    )

    fm = FastMail(mail_config)
    await fm.send_message(message)