from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, extract
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, EmailStr

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.models.history import AssessmentHistory
from app.models.payment import PaymentRecord
from app.models.settings import SystemSetting

router = APIRouter(prefix="/admin", tags=["Admin Dashboard"])

# ─── Schemas ───────────────────────────────────────────────────────────────────
class GrantAdminRequest(BaseModel):
    email: EmailStr

class UpdateSettingRequest(BaseModel):
    value: str

class UpdatePricingRequest(BaseModel):
    amount: float
    currency: str = "EGP"

class UpdateGatewayRequest(BaseModel):
    status: Optional[str] = None
    fees: Optional[str] = None
    fees_type: Optional[str] = None
    description: Optional[str] = None
    merchant_id: Optional[str] = None
    api_key: Optional[str] = None
    secret_key: Optional[str] = None
    mode: Optional[str] = None

# ─── Admin Guard ───────────────────────────────────────────────────────────────
async def get_admin_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


# ─── Overview Stats ────────────────────────────────────────────────────────────

@router.get("/stats", summary="Get dashboard key metrics")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    total_users = (await db.execute(select(func.count(User.id)))).scalar_one_or_none() or 0
    active_users = (await db.execute(select(func.count(User.id)).where(User.is_active == True))).scalar_one_or_none() or 0
    total_assessments = (await db.execute(select(func.count(AssessmentHistory.id)))).scalar_one_or_none() or 0
    total_videos = (await db.execute(
        select(func.count(AssessmentHistory.id)).where(AssessmentHistory.video_url.isnot(None))
    )).scalar_one_or_none() or 0
    
    # Calculate Total Revenue (only SUCCESS payments)
    total_revenue = (await db.execute(
        select(func.sum(PaymentRecord.amount)).where(PaymentRecord.status == "SUCCESS")
    )).scalar_one_or_none() or 0.0
    
    # Breakdown of Users by Age Demographic (for Pie Chart)
    users_dob_result = await db.execute(select(User.date_of_birth).where(User.date_of_birth.isnot(None)))
    dobs = users_dob_result.scalars().all()
    
    age_groups = {"Under 25": 0, "25-34": 0, "35-44": 0, "45+": 0}
    today = datetime.utcnow().date()
    for dob in dobs:
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        if age < 25: age_groups["Under 25"] += 1
        elif age < 35: age_groups["25-34"] += 1
        elif age < 45: age_groups["35-44"] += 1
        else: age_groups["45+"] += 1
        
    breakdown = {k: v for k, v in age_groups.items() if v > 0}
    if not breakdown:
        breakdown = {"No Data Yet": 1}

    # Journey Completion Rate (Drop-off Analysis)
    users_with_assessments_result = await db.execute(
        select(AssessmentHistory.user_id, AssessmentHistory.assessment_type)
        .order_by(AssessmentHistory.user_id, AssessmentHistory.created_at)
    )
    all_assessments = users_with_assessments_result.all()

    # Journey Completion Rate (Unique users per stage, non-sequential)
    user_journey = {}
    for user_id, assessment_type in all_assessments:
        if user_id not in user_journey:
            user_journey[user_id] = set()
        # Clean type name (lower case and strip)
        ptype = assessment_type.lower().strip()
        user_journey[user_id].add(ptype)

    journey_stages = {
        "Only Psychology": 0,
        "Psychology + Neuroscience": 0,
        "Psychology + Neuro + Letter": 0,
        "Psychology + Neuro + Letter + Astrology": 0,
        "Fully Completed": 0
    }

    # REVISED FUNNEL: Count cumulative users reaching each stage in the defined path
    # Even if they skip psychology, if they reached astrology, we often count them reaching that far
    # but the previous buckets were misleadingly mutually exclusive.
    # Let's count EXACTLY how many unique users have done EACH stage.
    unique_stage_counts = {
        "psychology": 0,
        "neuroscience": 0,
        "letter": 0,
        "astrology": 0,
        "comprehensive": 0
    }
    for completed_types in user_journey.values():
        for s in unique_stage_counts.keys():
            if s in completed_types:
                unique_stage_counts[s] += 1

    # Count exactly how many unique users have done EACH stage
    unique_stage_counts = {
        "Psychology": 0,
        "Neuroscience": 0,
        "Letter Science": 0,
        "Astrology": 0,
        "Comprehensive": 0
    }
    
    # Map database type names to the display labels used in the buckets
    type_map = {
        "psychology": "Psychology",
        "neuroscience": "Neuroscience",
        "letter": "Letter Science",
        "astrology": "Astrology",
        "comprehensive": "Comprehensive"
    }

    for completed_types in user_journey.values():
        for db_type, label in type_map.items():
            if db_type in completed_types:
                unique_stage_counts[label] += 1

    # Return the direct counts. 
    # NOTE: The frontend (app.js) was doing a cumulative sum, which we will now disable 
    # to show absolute unique user counts per stage. 
    # For now, we will use a specific key "absolute_counts" to signify this.
    
    # New users in last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    new_users_30d = (await db.execute(
        select(func.count(User.id)).where(User.created_at >= thirty_days_ago)
    )).scalar_one_or_none() or 0

    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_assessments": total_assessments,
        "total_videos": total_videos,
        "new_users_30d": new_users_30d,
        "total_revenue": total_revenue,
        "breakdown": breakdown,
        "journey": unique_stage_counts,
        "is_absolute": True # Flag for frontend
    }


@router.get("/users/growth", summary="Daily user registration counts (last 14 days)")
async def get_user_growth(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """Returns daily registration count for the last 14 days."""
    fourteen_days_ago = datetime.utcnow() - timedelta(days=14)
    # Truncate to date to group by day
    result = await db.execute(
        select(
            func.date(User.created_at).label("day"),
            func.count(User.id).label("count")
        )
        .where(User.created_at >= fourteen_days_ago)
        .group_by(func.date(User.created_at))
        .order_by(func.date(User.created_at))
    )
    rows = result.all()

    # Create a map of existing data
    data_map = {row.day: row.count for row in rows}
    
    # Fill in all 14 days, even if 0 registrations
    data = []
    for i in range(14, -1, -1):
        target_date = (datetime.utcnow() - timedelta(days=i)).date()
        count = data_map.get(target_date, 0)
        data.append({
            "month": target_date.strftime("%b %d"), # Keeping key as 'month' so frontend JS doesn't break
            "count": count
        })

    return data


# ─── User Management ───────────────────────────────────────────────────────────

@router.get("/users", summary="Get list of all users")
async def get_users(
    skip: int = 0,
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    result = await db.execute(select(User).order_by(User.created_at.desc()).offset(skip).limit(limit))
    users = result.scalars().all()

    # For each user, count their assessments
    user_ids = [u.id for u in users]
    counts_result = await db.execute(
        select(AssessmentHistory.user_id, func.count(AssessmentHistory.id))
        .where(AssessmentHistory.user_id.in_(user_ids))
        .group_by(AssessmentHistory.user_id)
    )
    counts_map = {str(row[0]): row[1] for row in counts_result.all()}

    return [
        {
            "id": str(u.id),
            "email": u.email,
            "fullname": u.fullname,
            "date_of_birth": str(u.date_of_birth) if u.date_of_birth else None,
            "place_of_birth": u.place_of_birth,
            "is_active": u.is_active,
            "is_verified": u.is_verified,
            "profile_picture_url": u.profile_picture_url,
            "created_at": u.created_at,
            "assessment_count": counts_map.get(str(u.id), 0)
        }
        for u in users
    ]


@router.get("/users/{user_id}/details", summary="Get single user details + their assessments")
async def get_user_details(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    assessments_result = await db.execute(
        select(AssessmentHistory)
        .where(AssessmentHistory.user_id == user_id)
        .order_by(AssessmentHistory.created_at.desc())
    )
    assessments = assessments_result.scalars().all()

    return {
        "id": str(user.id),
        "email": user.email,
        "fullname": user.fullname,
        "date_of_birth": str(user.date_of_birth) if user.date_of_birth else None,
        "place_of_birth": user.place_of_birth,
        "time_of_birth": str(user.time_of_birth) if user.time_of_birth else None,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "profile_picture_url": user.profile_picture_url,
        "created_at": user.created_at,
        "assessments": [
            {
                "id": str(a.id),
                "type": a.assessment_type,
                "has_video": a.video_url is not None,
                "video_url": a.video_url,
                "created_at": a.created_at,
            }
            for a in assessments
        ]
    }


@router.post("/users/{user_id}/toggle-status", summary="Toggle user active status")
async def toggle_user_status(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = not user.is_active
    await db.commit()
    return {"message": f"User is now {'Active' if user.is_active else 'Inactive'}", "is_active": user.is_active}


@router.delete("/users/{user_id}", summary="Delete a user and all their data")
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.delete(user)
    await db.commit()
    return {"message": "User deleted successfully"}


# ─── Assessment Management ─────────────────────────────────────────────────────

JOURNEY_STAGES = ["psychology", "neuroscience", "letter", "astrology", "comprehensive"]

@router.get("/assessments/journey", summary="Get user journey progress for all users")
async def get_user_journeys(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    # Get all users who have at least one assessment, ordered by their LATEST assessment date
    users_result = await db.execute(
        select(User)
        .join(AssessmentHistory, AssessmentHistory.user_id == User.id)
        .group_by(User.id)
        .order_by(func.max(AssessmentHistory.created_at).desc())
    )
    users = users_result.scalars().all()

    # For each user, get their set of completed assessment types
    user_ids = [u.id for u in users]
    assessments_result = await db.execute(
        select(
            AssessmentHistory.user_id,
            AssessmentHistory.assessment_type,
            AssessmentHistory.video_url,
            AssessmentHistory.created_at
        )
        .where(AssessmentHistory.user_id.in_(user_ids))
        .order_by(AssessmentHistory.created_at)
    )
    all_assessments = assessments_result.all()

    # Build per-user data
    user_data = {str(u.id): {
        "id": str(u.id),
        "name": u.fullname,
        "email": u.email,
        "completed_stages": set(),
        "has_video": False,
        "last_activity": None
    } for u in users}

    for row in all_assessments:
        uid = str(row.user_id)
        if uid in user_data:
            # Normalize assessment type
            clean_type = row.assessment_type.lower().strip()
            user_data[uid]["completed_stages"].add(clean_type)
            if row.video_url:
                user_data[uid]["has_video"] = True
            if not user_data[uid]["last_activity"] or row.created_at > user_data[uid]["last_activity"]:
                user_data[uid]["last_activity"] = row.created_at

    # Format output
    return [
        {
            "id": d["id"],
            "name": d["name"],
            "email": d["email"],
            "has_video": d["has_video"],
            "last_activity": d["last_activity"].isoformat() if d["last_activity"] else None,
            "stages": {
                stage: (stage in d["completed_stages"])
                for stage in JOURNEY_STAGES
            },
            "completed_count": len(d["completed_stages"]),
            "total_stages": len(JOURNEY_STAGES)
        }
        for d in user_data.values()
    ]


@router.get("/assessments", summary="Get all assessments")
async def get_assessments(
    skip: int = 0,
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    result = await db.execute(
        select(AssessmentHistory, User.email.label("user_email"), User.fullname)
        .join(User, AssessmentHistory.user_id == User.id)
        .order_by(AssessmentHistory.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    items = result.all()

    return [
        {
            "id": str(item.AssessmentHistory.id),
            "user_id": str(item.AssessmentHistory.user_id),
            "user_email": item.user_email,
            "user_name": item.fullname,
            "type": item.AssessmentHistory.assessment_type,
            "has_video": item.AssessmentHistory.video_url is not None,
            "video_url": item.AssessmentHistory.video_url,
            "created_at": item.AssessmentHistory.created_at
        }
        for item in items
    ]


@router.get("/assessments/{assessment_id}/result", summary="Get full result data of an assessment")
async def get_assessment_result(
    assessment_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    result = await db.execute(
        select(AssessmentHistory, User.email.label("user_email"), User.fullname)
        .join(User, AssessmentHistory.user_id == User.id)
        .where(AssessmentHistory.id == assessment_id)
    )
    item = result.first()
    if not item:
        raise HTTPException(status_code=404, detail="Assessment not found")

    return {
        "id": str(item.AssessmentHistory.id),
        "user_email": item.user_email,
        "user_name": item.fullname,
        "type": item.AssessmentHistory.assessment_type,
        "input_data": item.AssessmentHistory.input_data,
        "result_data": item.AssessmentHistory.result_data,
        "video_url": item.AssessmentHistory.video_url,
        "created_at": item.AssessmentHistory.created_at
    }


@router.delete("/assessments/{assessment_id}", summary="Delete an assessment record")
async def delete_assessment(
    assessment_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    result = await db.execute(select(AssessmentHistory).where(AssessmentHistory.id == assessment_id))
    assessment = result.scalar_one_or_none()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    await db.delete(assessment)
    await db.commit()
    return {"message": "Assessment deleted successfully"}


# ─── Payment Management (Admin) ────────────────────────────────────────────────

@router.get("/payments", summary="Get all payment records")
async def get_admin_payments(
    skip: int = 0,
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    result = await db.execute(
        select(PaymentRecord, User.email.label("user_email"), User.fullname)
        .join(User, PaymentRecord.user_id == User.id)
        .order_by(PaymentRecord.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    items = result.all()

    return [
        {
            "id": str(item.PaymentRecord.id),
            "user_id": str(item.PaymentRecord.user_id),
            "user_email": item.user_email,
            "user_name": item.fullname,
            "order_id": item.PaymentRecord.order_id,
            "session_id": item.PaymentRecord.session_id,
            "service_type": item.PaymentRecord.service_type,
            "amount": item.PaymentRecord.amount,
            "currency": item.PaymentRecord.currency,
            "status": item.PaymentRecord.status,
            "payment_method": item.PaymentRecord.payment_method,
            "created_at": item.PaymentRecord.created_at
        }
        for item in items
    ]


# ─── System Health ─────────────────────────────────────────────────────────────

@router.get("/health", summary="System health and API key status")
async def get_system_health(
    admin: User = Depends(get_admin_user)
):
    import os

    keys_to_check = [
        ("OPENAI_API_KEY", "OpenAI"),
        ("STABILITY_API_KEY", "Stability AI"),
        ("D_ID_API_KEY", "D-ID"),
        ("DATABASE_URL", "Database"),
        ("SECRET_KEY", "JWT Secret"),
        ("CLOUDINARY_CLOUD_NAME", "Cloudinary"),
    ]

    health_status = {}
    all_ok = True
    for env_key, label in keys_to_check:
        val = os.getenv(env_key)
        configured = bool(val and len(val) > 5)
        if not configured:
            all_ok = False
        health_status[label] = {
            "configured": configured,
            "status": "✓ Active" if configured else "✗ Missing"
        }

    return {
        "overall": "healthy" if all_ok else "degraded",
        "services": health_status,
        "platform": "Bayt Al Hayat (بيت الحياة) Admin Engine",
        "checked_at": datetime.utcnow().isoformat()
    }


# ─── Admin User Management ─────────────────────────────────────────────────────

@router.get("/admins", summary="List all admin users")
async def list_admins(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    result = await db.execute(
        select(User).where(User.is_admin == True)
    )
    admins = result.scalars().all()
    return [
        {
            "id": str(u.id),
            "email": u.email,
            "name": u.fullname,
            "created_at": u.created_at.isoformat() if u.created_at else None
        }
        for u in admins
    ]


@router.post("/admins/grant", summary="Grant admin access to a user by email")
async def grant_admin(
    body: GrantAdminRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found with that email")
    if user.is_admin:
        raise HTTPException(status_code=400, detail="User is already an admin")
    user.is_admin = True
    await db.commit()
    return {"message": f"✅ {user.fullname} ({user.email}) is now an admin"}


@router.delete("/admins/revoke/{user_id}", summary="Revoke admin access from a user")
async def revoke_admin(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if str(user.id) == str(admin.id):
        raise HTTPException(status_code=400, detail="Cannot revoke your own admin access")
    user.is_admin = False
    await db.commit()
    return {"message": f"❌ Admin access revoked for {user.fullname} ({user.email})"}


# ─── Settings: Pricing ────────────────────────────────────────────────────────
@router.get("/settings/pricing", summary="List pricing settings")
async def get_pricing_settings(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    # Services we currently offer
    services = [
        "final_report_video"
    ]
    
    # We query both price_* and currency_* keys
    keys_to_fetch = [f"price_{s}" for s in services] + [f"currency_{s}" for s in services]
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key.in_(keys_to_fetch))
    )
    rows = {r.key: r.value for r in result.scalars().all()}
    
    return [
        {
            "service_type": service,
            "amount": float(rows.get(f"price_{service}", "250.00")),  # Default Fallback
            "currency": rows.get(f"currency_{service}", "EGP")       # Default Currency Fallback
        }
        for service in services
    ]

@router.put("/settings/pricing/{service_id}", summary="Update a price setting")
async def update_pricing_setting(
    service_id: str,
    body: UpdatePricingRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    from datetime import datetime
    try:
        new_price = float(body.amount)
        if new_price < 0:
            raise ValueError()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid price amount. Must be a positive number.")

    price_key = f"price_{service_id}"
    currency_key = f"currency_{service_id}"
    
    # Save Price Amount
    result_price = await db.execute(select(SystemSetting).where(SystemSetting.key == price_key))
    setting_price = result_price.scalar_one_or_none()
    
    if not setting_price:
        setting_price = SystemSetting(
            key=price_key,
            value=f"{new_price:.2f}",
            group="pricing",
            label=f"Price For: {service_id.replace('_', ' ').title()}",
            description="Base price users pay for this service",
            is_secret=False
        )
        db.add(setting_price)
    else:
        setting_price.value = f"{new_price:.2f}"
        setting_price.updated_at = datetime.utcnow()

    # Save Currency
    new_currency = body.currency.strip().upper() or "EGP"
    result_curr = await db.execute(select(SystemSetting).where(SystemSetting.key == currency_key))
    setting_curr = result_curr.scalar_one_or_none()
    
    if not setting_curr:
        setting_curr = SystemSetting(
            key=currency_key,
            value=new_currency,
            group="pricing",
            label=f"Currency For: {service_id.replace('_', ' ').title()}",
            description="Currency used for this service price",
            is_secret=False
        )
        db.add(setting_curr)
    else:
        setting_curr.value = new_currency
        setting_curr.updated_at = datetime.utcnow()

    await db.commit()
    return {"message": f"✅ Pricing for {service_id.replace('_', ' ').title()} updated to {new_price:.2f} {new_currency}"}

# ─── Settings: AI Models ────────────────────────────────────────────────────────

def _mask(value: str, is_secret: bool) -> str:
    """Return masked value for secret keys, showing only first 8 chars."""
    if not is_secret or not value:
        return value or ""
    visible = value[:8]
    return visible + "•" * min(20, max(4, len(value) - 8))


@router.get("/settings/models", summary="List AI model settings")
async def get_model_settings(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.group == "ai_models").order_by(SystemSetting.key)
    )
    rows = result.scalars().all()

    # Fallback to env for keys missing from DB
    import os
    return [
        {
            "key": r.key,
            "label": r.label,
            "description": r.description,
            "is_secret": r.is_secret,
            "value": _mask(r.value or os.getenv(r.key.upper(), ""), r.is_secret),
            "has_value": bool(r.value),
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in rows
    ]


@router.put("/settings/models/{key}", summary="Update an AI model setting")
async def update_model_setting(
    key: str,
    body: UpdateSettingRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    from datetime import datetime
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == key, SystemSetting.group == "ai_models")
    )
    setting = result.scalar_one_or_none()
    if not setting:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")
    setting.value = body.value
    setting.updated_at = datetime.utcnow()
    await db.commit()
    return {"message": f"✅ '{setting.label}' updated successfully"}


@router.post("/settings/models/{key}/test", summary="Test an AI model connection")
async def test_model_setting(
    key: str,
    body: UpdateSettingRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    import httpx
    val = body.value.strip()

    try:
        if key == "openai_api_key":
            async with httpx.AsyncClient(timeout=5) as client:
                res = await client.get("https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {val}"})
                res.raise_for_status()
            return {"message": "OpenAI connection successful"}

        elif key == "stability_api_key":
            async with httpx.AsyncClient(timeout=5) as client:
                res = await client.get("https://api.stability.ai/v1/engines/list", headers={"Authorization": f"Bearer {val}"})
                res.raise_for_status()
            return {"message": "Stability AI connection successful"}

        elif key == "d_id_api_key":
            # D-ID uses basic auth, key is usually "username:password"
            # However some endpoints just accept basic auth with the full API key string if formatted correctly
            auth_header = f"Basic {__import__('base64').b64encode(val.encode()).decode()}" if ":" in val else f"Bearer {val}"
            async with httpx.AsyncClient(timeout=5) as client:
                res = await client.get("https://api.d-id.com/credits", headers={"Authorization": auth_header})
                res.raise_for_status()
            return {"message": "D-ID connection successful"}

        elif "key" in key or "secret" in key:
            if len(val) > 8:
                return {"message": f"Format OK (length: {len(val)}). Full automated test not available for this key."}
            else:
                raise HTTPException(status_code=400, detail="Key seems too short to be valid")

        return {"message": "Value looks OK"}

    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=400, detail=f"API rejected the key (Status {e.response.status_code})")
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Network error testing key: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")


# ─── Settings: Payment Gateways ────────────────────────────────────────────────

@router.get("/settings/gateways", summary="List payment gateways")
async def get_gateway_settings(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.group == "payment_gateway")
    )
    rows = result.scalars().all()
    data = {r.key: r for r in rows}

    def gv(k):
        """Get gateway value, masked if secret."""
        r = data.get(k)
        if not r:
            return ""
        return _mask(r.value or "", r.is_secret)

    return [
        {
            "id": "kashier",
            "name": "Kashier",
            "status": data.get("kashier_status", type("o", (), {"value": "inactive"})()).value,
            "fees": gv("kashier_fees"),
            "fees_type": gv("kashier_fees_type"),
            "description": gv("kashier_description"),
            "merchant_id": gv("kashier_merchant_id"),
            "api_key": gv("kashier_api_key"),
            "secret_key": gv("kashier_secret_key"),
            "mode": gv("kashier_mode"),
        }
    ]


@router.put("/settings/gateways/kashier", summary="Update Kashier gateway settings")
async def update_kashier_settings(
    body: UpdateGatewayRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    from datetime import datetime

    field_map = {
        "status": "kashier_status",
        "fees": "kashier_fees",
        "fees_type": "kashier_fees_type",
        "description": "kashier_description",
        "merchant_id": "kashier_merchant_id",
        "api_key": "kashier_api_key",
        "secret_key": "kashier_secret_key",
        "mode": "kashier_mode",
    }

    updated = []
    for field, db_key in field_map.items():
        val = getattr(body, field)
        if val is not None:
            result = await db.execute(select(SystemSetting).where(SystemSetting.key == db_key))
            setting = result.scalar_one_or_none()
            if setting:
                setting.value = val
                setting.updated_at = datetime.utcnow()
                updated.append(db_key)

    await db.commit()
    return {"message": f"✅ Kashier gateway updated ({len(updated)} fields)"}
