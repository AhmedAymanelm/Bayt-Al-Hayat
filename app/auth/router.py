from fastapi import APIRouter, Depends, status, BackgroundTasks, HTTPException, Request
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
    VerifyResetCodeRequest,
    VerifyResetCodeResponse,
    ResetPasswordRequest,
    MessageResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    UserResponse,
)
from app.auth.service import (
    register_user,
    login_user,
    forget_password,
    verify_reset_code,
    reset_password,
    refresh_token_service,
    logout,
)
from app.auth.dependencies import get_current_user
from app.auth.models import User
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter(prefix="/auth", tags=["Authentication"])
limiter = Limiter(key_func=get_remote_address)


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
@limiter.limit("10/minute")
async def register(
    request: Request,
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
@limiter.limit("5/minute")
async def login(
    request: Request,
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
@limiter.limit("5/minute")
async def login_swagger(
    request: Request,
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
@limiter.limit("3/minute")
async def forget_password_route(
    request: Request,
    data: ForgetPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    return await forget_password(data, background_tasks, db)


@router.post(
    "/verify-reset-code",
    response_model=VerifyResetCodeResponse,
    summary="Verify reset code",
)
@limiter.limit("3/minute")
async def verify_reset_code_route(
    request: Request,
    data: VerifyResetCodeRequest,
    db: AsyncSession = Depends(get_db),
):
    return await verify_reset_code(data, db)


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Reset password using email and code",
)
@limiter.limit("3/minute")
async def reset_password_route(
    request: Request,
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
