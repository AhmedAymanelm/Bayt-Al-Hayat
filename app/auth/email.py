import os
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from dotenv import load_dotenv

load_dotenv(override=True)

conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME", ""),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD", ""),
    MAIL_FROM=os.getenv("MAIL_FROM", ""),
    MAIL_PORT=int(os.getenv("MAIL_PORT", 587)),
    MAIL_SERVER=os.getenv("MAIL_SERVER", "smtp.gmail.com"),
    MAIL_STARTTLS=os.getenv("MAIL_STARTTLS", "True").lower() in ["true", "1", "t"],
    MAIL_SSL_TLS=os.getenv("MAIL_SSL_TLS", "False").lower() in ["true", "1", "t"],
    USE_CREDENTIALS=os.getenv("USE_CREDENTIALS", "True").lower() in ["true", "1", "t"],
    VALIDATE_CERTS=os.getenv("VALIDATE_CERTS", "True").lower() in ["true", "1", "t"],
)


async def send_verification_email(email_to: str, token: str):
    html = f"""
    <div dir="rtl" style="font-family: Arial, sans-serif; text-align: right; padding: 20px;">
        <h2>تأكيد حساب أبراغ</h2>
        <p>مرحباً بك! لتأكيد حسابك، انسخ الكود التالي:</p>
        <div style="background: #f4f4f4; padding: 15px; margin: 20px 0; border-radius: 5px; word-break: break-all; text-align: left;" dir="ltr">
            <strong>{token}</strong>
        </div>
        <p>هذا الكود صالح لمدة 24 ساعة.</p>
    </div>
    """
    
    message = MessageSchema(
        subject="تأكيد حسابك - Abrag",
        recipients=[email_to],
        body=html,
        subtype=MessageType.html
    )
    
    fm = FastMail(conf)
    await fm.send_message(message)


async def send_reset_password_email(email_to: str, token: str):
    html = f"""
    <div dir="rtl" style="font-family: Arial, sans-serif; text-align: right; padding: 20px;">
        <h2>إعادة تعيين كلمة المرور</h2>
        <p>لقد طلبت إعادة تعيين كلمة المرور الخاصة بك. يرجى استخدام الكود التالي:</p>
        <div style="background: #f4f4f4; padding: 15px; margin: 20px 0; border-radius: 5px; word-break: break-all; text-align: left;" dir="ltr">
            <strong>{token}</strong>
        </div>
        <p>هذا الكود صالح لمدة 15 دقيقة.</p>
        <p>إذا لم تطلب هذا، يمكنك تجاهل هذه الرسالة.</p>
    </div>
    """
    
    message = MessageSchema(
        subject="إعادة تعيين كلمة المرور - Abrag",
        recipients=[email_to],
        body=html,
        subtype=MessageType.html
    )
    
    fm = FastMail(conf)
    await fm.send_message(message)
