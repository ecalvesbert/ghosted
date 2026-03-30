from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    invite_code: str


class TokenRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    token: str


class BootstrapRequest(BaseModel):
    email: EmailStr
    password: str
    admin_secret: str
