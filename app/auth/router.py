from fastapi import APIRouter, Depends, status, BackgroundTasks, UploadFile, File, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from app.database import get_db
from app.auth.schemas import (
    UserRegisterRequest,
    RegisterResponse,
    LoginRequest,
    LoginResponse,
    ForgetPasswordRequest,
    ForgetPasswordResponse,
    ResetPasswordRequest,
    MessageResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    VerifyAccountRequest,
    UserResponse,
)
from app.auth.service import (
    register_user,
    login_user,
    forget_password,
    reset_password,
    refresh_token_service,
    verify_account,
    logout,
)
from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.auth.cloudinary_service import upload_profile_picture, delete_profile_picture

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(
    user_data: UserRegisterRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    return await register_user(user_data, background_tasks, db)


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login and get access/refresh tokens",
)
async def login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Standard JSON login endpoint for frontend applications (e.g. Flutter)"""
    return await login_user(login_data, db)


@router.post(
    "/login/swagger",
    summary="OAuth2 Token endpoint for Swagger UI",
    include_in_schema=False,
)
async def login_swagger(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: AsyncSession = Depends(get_db),
):
    """Dedicated endpoint specifically formatted for Swagger UI OAuth2 requirements"""
    login_req = LoginRequest(email=form_data.username, password=form_data.password)
    response = await login_user(login_req, db)
    
    return {
        "access_token": response["access_token"],
        "token_type": response["token_type"],
    }


@router.post(
    "/forget-password",
    response_model=ForgetPasswordResponse,
    summary="Request a password reset token",
)
async def forget_password_route(
    data: ForgetPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    return await forget_password(data, background_tasks, db)


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Reset password using reset token",
)
async def reset_password_route(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    return await reset_password(data, db)


@router.post(
    "/refresh-token",
    response_model=RefreshTokenResponse,
    summary="Get new tokens using refresh token",
)
async def refresh_token_route(
    data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    return await refresh_token_service(data.refresh_token, db)


@router.post(
    "/verify-account",
    response_model=MessageResponse,
    summary="Verify account using 6-digit verification code",
)
async def verify_account_route(
    data: VerifyAccountRequest,
    db: AsyncSession = Depends(get_db),
):
    return await verify_account(data.email, data.verification_code, db)


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout (client should delete tokens)",
)
async def logout_route():
    return await logout()


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
async def get_me(current_user: User = Depends(get_current_user)):
    """Returns the currently authenticated user's profile"""
    return current_user


@router.post(
    "/profile-picture",
    response_model=UserResponse,
    summary="Upload or update profile picture",
)
async def upload_profile_picture_route(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a profile picture (max 5MB, jpg/png/webp)"""
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Only JPG, PNG, and WebP images are allowed"
        )
    
    # Validate file size (5MB max)
    file_bytes = await file.read()
    if len(file_bytes) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="File size must be less than 5MB"
        )
    
    # Upload to Cloudinary
    image_url = await upload_profile_picture(file_bytes, str(current_user.id))
    
    # Save URL to database
    current_user.profile_picture_url = image_url
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    
    return current_user


@router.delete(
    "/profile-picture",
    response_model=MessageResponse,
    summary="Delete profile picture",
)
async def delete_profile_picture_route(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove the current user's profile picture"""
    if not current_user.profile_picture_url:
        raise HTTPException(status_code=404, detail="No profile picture to delete")
    
    # Delete from Cloudinary
    await delete_profile_picture(str(current_user.id))
    
    # Remove URL from database
    current_user.profile_picture_url = None
    db.add(current_user)
    await db.commit()
    
    return {"message": "Profile picture deleted successfully"}
