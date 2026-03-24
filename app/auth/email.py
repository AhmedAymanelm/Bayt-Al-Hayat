import os
import httpx
from dotenv import load_dotenv

load_dotenv(override=True)

# Brevo HTTP API (works on Railway - no SMTP port blocking)
BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
MAIL_FROM = os.getenv("MAIL_FROM", "sirahmedayman@gmail.com")
MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME", "بيت الحياة")

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


async def _send_email(to_email: str, subject: str, html_content: str):
    """Send email using Brevo HTTP API (bypasses SMTP port blocking on Railway)"""
    headers = {
        "api-key": BREVO_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    payload = {
        "sender": {"name": MAIL_FROM_NAME, "email": MAIL_FROM},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html_content,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(BREVO_API_URL, json=payload, headers=headers)
        if response.status_code not in [200, 201]:
            print(f"Email send failed: {response.status_code} - {response.text}")
            raise Exception(f"Failed to send email: {response.text}")
        print(f"Email sent successfully to {to_email}")


async def send_verification_email(email_to: str, token: str):
    html = f"""
    <div dir="rtl" style="font-family: Arial, sans-serif; text-align: right; padding: 20px;">
        <h2>تأكيد حساب بيت الحياة</h2>
        <p>مرحباً بك! لتأكيد حسابك، انسخ الكود التالي:</p>
        <div style="background: #f4f4f4; padding: 15px; margin: 20px 0; border-radius: 5px; word-break: break-all; text-align: left;" dir="ltr">
            <strong>{token}</strong>
        </div>
        <p>هذا الكود صالح لمدة 24 ساعة.</p>
    </div>
    """
    await _send_email(email_to, "تأكيد حسابك - بيت الحياة", html)


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
    await _send_email(email_to, "إعادة تعيين كلمة المرور - بيت الحياة", html)
