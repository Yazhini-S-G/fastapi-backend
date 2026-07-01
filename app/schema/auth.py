from pydantic import BaseModel, EmailStr, Field, field_validator

BCRYPT_MAX_PASSWORD_BYTES = 72
PASSWORD_TOO_LONG_MESSAGE = "Password must be 72 bytes or fewer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)

    @field_validator("password")
    @classmethod
    def validate_bcrypt_password_length(cls, value: str) -> str:
        if len(value.encode("utf-8")) > BCRYPT_MAX_PASSWORD_BYTES:
            msg = PASSWORD_TOO_LONG_MESSAGE
            raise ValueError(msg)
        return value


class ProfileResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str = ""
    account_status: str = "Active"


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    message: str


class ResetPasswordRequest(BaseModel):
    reset_token: str = Field(min_length=1)
    new_password: str = Field(min_length=8)
    confirm_password: str = Field(min_length=8)

    @field_validator("new_password", "confirm_password")
    @classmethod
    def validate_bcrypt_password_length(cls, value: str) -> str:
        if len(value.encode("utf-8")) > BCRYPT_MAX_PASSWORD_BYTES:
            msg = PASSWORD_TOO_LONG_MESSAGE
            raise ValueError(msg)
        return value


class ResetPasswordResponse(BaseModel):
    message: str


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8)
    confirm_password: str = Field(min_length=8)

    @field_validator("old_password", "new_password", "confirm_password")
    @classmethod
    def validate_bcrypt_password_length(cls, value: str) -> str:
        if len(value.encode("utf-8")) > BCRYPT_MAX_PASSWORD_BYTES:
            msg = PASSWORD_TOO_LONG_MESSAGE
            raise ValueError(msg)
        return value


class ChangePasswordResponse(BaseModel):
    message: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class RefreshTokenResponse(BaseModel):
    access_token: str
    token_type: str


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8)
    confirm_password: str = Field(min_length=8)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        name = value.strip()
        if not name:
            msg = "Name is required"
            raise ValueError(msg)
        return name

    @field_validator("password", "confirm_password")
    @classmethod
    def validate_bcrypt_password_length(cls, value: str) -> str:
        if len(value.encode("utf-8")) > BCRYPT_MAX_PASSWORD_BYTES:
            msg = PASSWORD_TOO_LONG_MESSAGE
            raise ValueError(msg)
        return value
