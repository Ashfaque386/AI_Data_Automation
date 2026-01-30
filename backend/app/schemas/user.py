"""
User Schemas
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


class PermissionBase(BaseModel):
    name: str
    description: Optional[str] = None
    resource: Optional[str] = None
    action: Optional[str] = None


class PermissionResponse(PermissionBase):
    id: int
    
    class Config:
        from_attributes = True


class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None


class RoleCreate(RoleBase):
    permission_ids: List[int] = []


class RoleResponse(RoleBase):
    id: int
    is_system: bool
    permissions: List[PermissionResponse] = []
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    role_ids: List[int] = []


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    role_ids: Optional[List[int]] = None


class UserResponse(UserBase):
    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    roles: List[RoleResponse] = []
    
    class Config:
        from_attributes = True


class UserInDB(UserResponse):
    hashed_password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenPayload(BaseModel):
    sub: int
    email: str
    exp: datetime
    type: str = "access"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)
