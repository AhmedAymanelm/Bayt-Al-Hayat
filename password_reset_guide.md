# Password Reset Flow Refactor

Successfully split the password reset process into three modular steps for better security and API flexibility.

## Postman Implementation

### 1. Request Reset Code (Forgot Password)
**Endpoint:** `POST /api/v1/auth/forget-password`
**Body (JSON):**
```json
{
  "email": "user@example.com"
}
```

### 2. Verify Code & Get Reset Token
**Endpoint:** `POST /api/v1/auth/verify-reset-code`
**Body (JSON):**
```json
{
  "email": "user@example.com",
  "verification_code": "123456"
}
```
**Response:**
```json
{
  "reset_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "message": "تم التحقق من الرمز بنجاح. يمكنك الآن تعيين كلمة مرور جديدة."
}
```

### 3. Set New Password
**Endpoint:** `POST /api/v1/auth/reset-password`
**Header:** `Authorization: Bearer <reset_token_from_step_2>`
**Body (JSON):**
```json
{
  "new_password": "NewSecurePassword123"
}
```

## Key Changes
- Created `VerifyResetCodeRequest` and `VerifyResetCodeResponse` schemas.
- Added `verify_reset_code` service to handle intermediate verification.
- Implemented `get_reset_password_email` dependency to securely extract identity from the short-lived reset token.
- Updated `reset_password` to accept only `new_password` in the request body.
