"""
Authentication Router - UC1: User Registration and Login
"""
from fastapi import APIRouter, HTTPException, status, Depends
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from datetime import datetime
import logging

from models.user import UserCreate, UserLogin, UserResponse, TokenResponse
from utils.jwt_handler import create_access_token, get_current_user
from utils.validators import validate_email, validate_password
from database import get_db_cursor

router = APIRouter()
logger = logging.getLogger(__name__)

# Password hashing with Argon2
ph = PasswordHasher()


def hash_password(password: str) -> str:
    return ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        ph.verify(hashed_password, plain_password)
        return True
    except VerifyMismatchError:
        return False
    except Exception:
        return False


@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserCreate):
    """
    Register a new user account
    FR1: Secure account creation
    """
    # Validate email
    is_valid, error = validate_email(user_data.email)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error)
    
    # Validate password
    is_valid, error = validate_password(user_data.password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error)
    
    try:
        with get_db_cursor() as cursor:
            # Check if email exists
            cursor.execute(
                "SELECT id FROM users WHERE email = %s",
                (user_data.email.lower(),)
            )
            if cursor.fetchone():
                raise HTTPException(
                    status_code=400,
                    detail="Email already registered"
                )
            
            # Create user
            password_hash = hash_password(user_data.password)
            cursor.execute(
                """INSERT INTO users (email, password_hash, name, created_at, role)
                   VALUES (%s, %s, %s, %s, 'student')""",
                (user_data.email.lower(), password_hash, user_data.name, datetime.now())
            )
            user_id = cursor.lastrowid
            
            # Create default user settings
            cursor.execute(
                """INSERT INTO user_settings (user_id, notifications_enabled, daily_goal_minutes)
                   VALUES (%s, TRUE, 15)""",
                (user_id,)
            )
            
            # Generate token
            token = create_access_token({
                "sub": str(user_id),
                "email": user_data.email.lower(),
                "role": "student"
            })
            
            return TokenResponse(
                access_token=token,
                user=UserResponse(
                    id=user_id,
                    email=user_data.email.lower(),
                    name=user_data.name,
                    cefr_level=None,
                    xp_total=0,
                    current_streak=0,
                    longest_streak=0,
                    role="student",
                    created_at=datetime.now().isoformat()
                )
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    """
    User login
    FR1: Secure login with email/password
    """
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                """SELECT id, email, password_hash, name, cefr_level, 
                          xp_total, current_streak, longest_streak, role, created_at
                   FROM users WHERE email = %s""",
                (credentials.email.lower(),)
            )
            user = cursor.fetchone()
            
            if not user or not verify_password(credentials.password, user["password_hash"]):
                raise HTTPException(
                    status_code=401,
                    detail="Invalid email or password"
                )
            
            # Update last login
            cursor.execute(
                "UPDATE users SET last_login = %s WHERE id = %s",
                (datetime.now(), user["id"])
            )
            
            # Generate token
            token = create_access_token({
                "sub": str(user["id"]),
                "email": user["email"],
                "role": user["role"]
            })
            
            return TokenResponse(
                access_token=token,
                user=UserResponse(
                    id=user["id"],
                    email=user["email"],
                    name=user["name"],
                    cefr_level=user["cefr_level"],
                    xp_total=user["xp_total"] or 0,
                    current_streak=user["current_streak"] or 0,
                    longest_streak=user["longest_streak"] or 0,
                    role=user["role"],
                    created_at=user["created_at"].isoformat() if user["created_at"] else ""
                )
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current authenticated user information"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                """SELECT id, email, name, cefr_level, xp_total, 
                          current_streak, longest_streak, role, created_at
                   FROM users WHERE id = %s""",
                (current_user["user_id"],)
            )
            user = cursor.fetchone()
            
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            return UserResponse(
                id=user["id"],
                email=user["email"],
                name=user["name"],
                cefr_level=user["cefr_level"],
                xp_total=user["xp_total"] or 0,
                current_streak=user["current_streak"] or 0,
                longest_streak=user["longest_streak"] or 0,
                role=user["role"],
                created_at=user["created_at"].isoformat() if user["created_at"] else ""
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user info")


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """
    Logout user (client should discard token)
    """
    return {"message": "Logged out successfully"}
