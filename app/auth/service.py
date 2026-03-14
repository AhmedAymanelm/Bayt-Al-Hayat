from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status, BackgroundTasks
from jose import JWTError

from app.auth.email import send_verification_email, send_reset_password_email

from app.auth.models import User
from app.auth.schemas import UserRegisterRequest, LoginRequest, ForgetPasswordRequest, ResetPasswordRequest
from app.auth.utils import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    create_reset_token,
    create_verification_code,
    decode_token,
)
from datetime import datetime, timedelta


async def register_user(user_data: UserRegisterRequest, background_tasks: BackgroundTasks, db: AsyncSession) -> dict:
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new user with hashed password
    new_user = User(
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        date_of_birth=user_data.date_of_birth,
        place_of_birth=user_data.place_of_birth,
        time_of_birth=user_data.time_of_birth,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Generate 6-digit verification code
    verification_code = create_verification_code()
    
    # Save code to user
    new_user.verification_code = verification_code
    new_user.verification_code_expires_at = datetime.utcnow() + timedelta(hours=24)
    db.add(new_user)
    await db.commit()

    # Send verification email in background
    background_tasks.add_task(send_verification_email, new_user.email, verification_code)

    return {
        "message": "User registered successfully. Please check your email for the verification code.",
        "user": new_user,
    }


async def login_user(login_data: LoginRequest, db: AsyncSession) -> dict:
    # Find user by email
    result = await db.execute(select(User).where(User.email == login_data.email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Verify password
    if not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Check if account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )

    # Generate tokens
    token_data = {"sub": str(user.id), "email": user.email}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user,
    }


async def forget_password(data: ForgetPasswordRequest, background_tasks: BackgroundTasks, db: AsyncSession) -> dict:
    # Check if email exists
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user:
        # Return same message even if email doesn't exist (security)
        return {
            "message": "If this email is registered, a reset token has been generated",
            "reset_token": "",
        }

    # Generate reset token (15 min expiry)
    reset_token = create_reset_token(user.email)

    # Send reset password email in background
    background_tasks.add_task(send_reset_password_email, user.email, reset_token)

    return {
        "message": "If this email is registered, a password reset token has been sent.",
        "reset_token": reset_token,
    }


async def reset_password(data: ResetPasswordRequest, db: AsyncSession) -> dict:
    # Decode and validate the reset token
    try:
        payload = decode_token(data.reset_token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    # Verify it's a reset token
    if payload.get("type") != "reset":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token type"
        )

    email = payload.get("sub")

    # Find user
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Update password
    user.hashed_password = hash_password(data.new_password)
    await db.commit()

    return {"message": "Password reset successfully"}


async def refresh_token_service(refresh_token: str, db: AsyncSession) -> dict:
    # Decode and validate the refresh token
    try:
        payload = decode_token(refresh_token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    # Verify it's a refresh token
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )

    user_id = payload.get("sub")
    email = payload.get("email")

    # Verify user still exists and is active
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or deactivated"
        )

    # Generate new tokens
    token_data = {"sub": str(user.id), "email": user.email}
    new_access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token(token_data)

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }


async def verify_account(email: str, verification_code: str, db: AsyncSession) -> dict:
    # Find user
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if user.is_verified:
        return {"message": "Account is already verified"}

    # Check if code matches
    if user.verification_code != verification_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code"
        )

    # Check expiration
    expires_at = user.verification_code_expires_at
    if not expires_at or expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code expired"
        )

    # Mark user as verified and clear the code
    user.is_verified = True
    user.verification_code = None
    user.verification_code_expires_at = None
    await db.commit()

    return {"message": "Account verified successfully"}


async def logout() -> dict:
    # With JWT, logout is handled client-side by deleting the tokens
    # In a more advanced setup, we'd blacklist the token
    return {"message": "Logged out successfully. Please delete your tokens."}
