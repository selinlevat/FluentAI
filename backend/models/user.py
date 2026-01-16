"""
User Models
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class CEFRLevel(str, Enum):
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"
    C2 = "C2"


class UserRole(str, Enum):
    STUDENT = "student"
    ADMIN = "admin"


class UserBase(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=2, max_length=100)


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class User(UserBase):
    id: int
    cefr_level: Optional[CEFRLevel] = None
    xp_total: int = 0
    current_streak: int = 0
    longest_streak: int = 0
    role: UserRole = UserRole.STUDENT
    created_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserInDB(User):
    password_hash: str


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    cefr_level: Optional[str] = None
    xp_total: int
    current_streak: int
    longest_streak: int
    role: str
    created_at: str


class UserSettings(BaseModel):
    user_id: int
    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    preferred_ai: str = "openai"
    notifications_enabled: bool = True
    daily_goal_minutes: int = 15
    study_days: List[str] = ["monday", "tuesday", "wednesday", "thursday", "friday"]


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
