from pydantic import BaseModel, EmailStr
from typing import Optional


# Login request
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# Signup request
class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


# Token response
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# Authenticated user response
class AuthUser(BaseModel):
    id: int
    name: str
    email: EmailStr