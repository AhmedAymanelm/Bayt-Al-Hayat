from fastapi import APIRouter, Depends, status, BackgroundTasks
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
    include_in_schema=False, # Hide this from the main docs since it's just for the Authorize button
)
async def login_swagger(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: AsyncSession = Depends(get_db),
):
    """Dedicated endpoint specifically formatted for Swagger UI OAuth2 requirements"""
    login_req = LoginRequest(email=form_data.username, password=form_data.password)
    response = await login_user(login_req, db)
    
    # Swagger Authorize explicitly needs exactly these fields without nesting
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
