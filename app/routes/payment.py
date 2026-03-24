from fastapi import APIRouter, HTTPException, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
import httpx
import os
import uuid
from datetime import datetime, timedelta

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.models.payment import PaymentRecord

payment_router = APIRouter(
    prefix="/payment",
    tags=["Payment (Kashier)"]
)
limiter = Limiter(key_func=get_remote_address)


async def _get_setting(key: str, fallback_env: str = "", default: str = "") -> str:
    """Read a setting from system_settings DB, fallback to env var."""
    try:
        from app.database import async_session_maker
        from app.models.settings import SystemSetting
        from sqlalchemy.future import select as _select
        async with async_session_maker() as sess:
            res = await sess.execute(_select(SystemSetting).where(SystemSetting.key == key))
            row = res.scalar_one_or_none()
            if row and row.value:
                return row.value
    except Exception:
        pass
    return os.environ.get(fallback_env, default)


async def _get_kashier_config():
    """Returns all Kashier config from DB (or env fallback)."""
    merchant_id = await _get_setting("kashier_merchant_id", "KASHIER_MERCHANT_ID")
    api_key     = await _get_setting("kashier_api_key",     "KASHIER_API_KEY")
    secret_key  = await _get_setting("kashier_secret_key",  "KASHIER_SECRET_KEY") or api_key
    mode        = await _get_setting("kashier_mode",        "KASHIER_MODE", "test")
    base        = "https://test-api.kashier.io" if mode == "test" else "https://api.kashier.io"
    return merchant_id, api_key, secret_key, mode, base


class PaymentRequest(BaseModel):
    # 'amount' and 'currency' discouraged from being trusted from client side. We compute it server side.
    service_type: str = "final_report_video"

@payment_router.get("/price")
async def get_service_price(service_type: str = "final_report_video"):
    """
    Returns the current price for a requested service.
    Flutter should call this to display the correct price on the UI.
    """
    price_str = await _get_setting(f"price_{service_type}", default="250.00")
    currency = await _get_setting(f"currency_{service_type}", default="EGP")
    try:
        price = float(price_str)
    except ValueError:
        price = 250.00
    
    return {
        "service_type": service_type,
        "amount": price,
        "currency": currency
    }

@payment_router.post("/checkout")
@limiter.limit("10/minute")
async def create_checkout_session(request: Request, body: PaymentRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    Create a Kashier Payment Session using the v3 API.
    The amount and currency are securely fetched from the database settings to prevent client-side tampering.
    """
    merchant_id, api_key, secret_key, mode, api_base = await _get_kashier_config()

    if not merchant_id or not api_key:
        raise HTTPException(status_code=500, detail="Kashier credentials are not configured")

    # Securely determine the amount and currency from the server config
    price_str = await _get_setting(f"price_{body.service_type}", default="250.00")
    currency = await _get_setting(f"currency_{body.service_type}", default="EGP")
    
    try:
        amount = float(price_str)
    except ValueError:
        amount = 250.00
        
    order_id = f"ORD_{str(uuid.uuid4()).replace('-', '')[:8]}"
    expire_at = (datetime.utcnow() + timedelta(hours=2)).isoformat() + "Z"

    payload = {
        "expireAt": expire_at,
        "maxFailureAttempts": 3,
        "paymentType": "credit",
        "amount": str(amount),
        "currency": currency,
        "order": order_id,
        "merchantRedirect": "https://baytalhayat.redirect/payment-success",
        "display": "en",
        "type": "one-time",
        "allowedMethods": "card,wallet",
        "iframeBackgroundColor": "#FFFFFF",
        "merchantId": merchant_id,
        "description": f"Payment for {body.service_type.replace('_', ' ').title()}",
        "manualCapture": False,
        "customer": {
            "email": current_user.email,
            "reference": str(current_user.id)
        },
        "saveCard": "optional",
        "retrieveSavedCard": True,
        "interactionSource": "ECOMMERCE",
        "enable3DS": True
    }

    headers = {
        "Authorization": secret_key,
        "api-key": api_key,
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{api_base}/v3/payment/sessions", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            session_id = data.get("_id")

            payment_record = PaymentRecord(
                user_id=current_user.id,
                order_id=order_id,
                session_id=session_id,
                amount=amount,
                currency=currency,
                service_type=body.service_type,
                status="PENDING"
            )
            db.add(payment_record)
            await db.commit()

            return {
                "message": "Payment session created successfully",
                "session_id": session_id,
                "session_url": data.get("sessionUrl"),
                "order_id": order_id,
                "amount": amount
            }
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Kashier API Error: {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@payment_router.post("/verify")
async def verify_payment(session_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    Called by the Flutter app after the checkout UI returns.
    Verifies the payment session status with Kashier and updates the DB.
    """
    _, api_key, secret_key, _, api_base = await _get_kashier_config()
    headers = {
        "Authorization": secret_key,
        "api-key": api_key
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{api_base}/v3/payment/sessions/{session_id}/payment", headers=headers)
            response.raise_for_status()
            data = response.json().get("data", {})
            kashier_status = data.get("status")

            result = await db.execute(select(PaymentRecord).where(PaymentRecord.session_id == session_id, PaymentRecord.user_id == current_user.id))
            payment_record = result.scalar_one_or_none()

            if not payment_record:
                raise HTTPException(status_code=404, detail="Payment record not found")

            if kashier_status in ("CAPTURED", "SUCCESS", "PAID", "APPROVED"):
                payment_record.status = "SUCCESS"
            elif kashier_status in ("FAILED", "DECLINED", "REJECTED", "CANCELLED"):
                payment_record.status = "FAILED"

            payment_record.payment_method = data.get("method")
            await db.commit()

            return {
                "status": payment_record.status,
                "order_id": payment_record.order_id,
                "amount": payment_record.amount
            }
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Kashier API Error: {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@payment_router.get("/status/{session_id}")
async def get_payment_status(session_id: str):
    """
    Get the status of a Kashier Payment Session.
    """
    _, api_key, secret_key, _, api_base = await _get_kashier_config()
    headers = {
        "Authorization": secret_key,
        "api-key": api_key
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{api_base}/v3/payment/sessions/{session_id}/payment", headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Kashier API Error: {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@payment_router.post("/webhook")
async def kashier_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Webhook endpoint to receive payment status updates from Kashier.
    Kashier sends a POST with JSON body + HMAC signature header.
    """
    import hmac
    import hashlib
    import json

    body_bytes = await request.body()
    raw_body = body_bytes.decode("utf-8") if body_bytes else "{}"
    signature_header = request.headers.get("x-kashier-signature") or request.headers.get("signature", "")

    # ── Mandatory HMAC signature verification ────────────────────────────────
    _, _, secret, _, _ = await _get_kashier_config()
    if not secret:
        raise HTTPException(status_code=500, detail="Webhook secret not configured on server")
    if not signature_header:
        return {"status": "ignored", "reason": "missing_signature"}

    import hmac as _hmac
    import hashlib
    expected_sig = _hmac.new(
        secret.encode("utf-8"),
        body_bytes,
        hashlib.sha256
    ).hexdigest()
    if not _hmac.compare_digest(expected_sig, signature_header):
        print("⚠️  Kashier webhook: invalid signature, rejecting.")
        return {"status": "ignored", "reason": "invalid_signature"}

    try:
        payload = json.loads(raw_body)
    except Exception:
        return {"status": "ignored", "reason": "invalid_json"}

    print("================ KASHIER WEBHOOK ================")
    print(payload)
    print("=================================================")

    # ── Extract fields ────────────────────────────────────────────────────────
    order_id       = payload.get("orderId") or payload.get("order_id")
    session_id     = payload.get("sessionId") or payload.get("session_id") or payload.get("_id")
    kashier_status = payload.get("status") or payload.get("paymentStatus", "")
    payment_method = payload.get("paymentMethod") or payload.get("method")

    if not order_id and not session_id:
        return {"status": "ignored", "reason": "no_order_id"}

    # ── Find payment record ───────────────────────────────────────────────────
    result = await db.execute(
        select(PaymentRecord).where(
            or_(
                PaymentRecord.order_id == order_id,
                PaymentRecord.session_id == session_id
            )
        )
    )
    payment = result.scalar_one_or_none()

    if not payment:
        print(f"⚠️  Webhook: no PaymentRecord found for order={order_id} session={session_id}")
        return {"status": "not_found"}

    # ── Map Kashier status → our status ───────────────────────────────────────
    if kashier_status.upper() in ("CAPTURED", "SUCCESS", "PAID", "APPROVED"):
        payment.status = "SUCCESS"
    elif kashier_status.upper() in ("FAILED", "DECLINED", "REJECTED", "CANCELLED", "EXPIRED"):
        payment.status = "FAILED"
    else:
        payment.status = "PENDING"

    if payment_method:
        payment.payment_method = payment_method

    payment.updated_at = datetime.utcnow()
    await db.commit()

    print(f"✅ Payment {payment.order_id} → {payment.status}")
    return {"status": "ok", "order_id": payment.order_id, "new_status": payment.status}
