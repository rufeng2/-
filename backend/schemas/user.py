"""
用户相关 Pydantic 模型
"""
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=12, max_length=128)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=4, max_length=128)
    display_name: str = ""


class TokenResponse(BaseModel):
    code: int = 200
    msg: str = "成功"
    token: str = ""
    role: str = "user"
    username: str = ""


class UserInfo(BaseModel):
    id: str = ""
    username: str = ""
    display_name: str = ""
    email: str = ""
    role: str = "user"
    department: str = ""
    is_active: bool = True


class AdminUserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=4, max_length=128)
    display_name: str = ""
    department: str = ""
    role: str = "user"
