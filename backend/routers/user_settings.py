"""
User Settings Router - UC16, UC17: Profile and API Key Management
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
import logging

from utils.jwt_handler import get_current_user
from utils.encryption import encrypt_api_key, decrypt_api_key, mask_api_key
from database import get_db_cursor

router = APIRouter()
logger = logging.getLogger(__name__)


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    daily_goal_minutes: Optional[int] = None
    notifications_enabled: Optional[bool] = None


class APIKeyUpdate(BaseModel):
    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    preferred_ai: Optional[str] = None


@router.get("/profile")
async def get_profile(current_user: dict = Depends(get_current_user)):
    """Get user profile and settings"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                """SELECT u.id, u.email, u.name, u.cefr_level, u.xp_total,
                          u.current_streak, u.created_at,
                          s.daily_goal_minutes, s.notifications_enabled,
                          s.study_days, s.preferred_ai,
                          s.openai_api_key, s.gemini_api_key
                   FROM users u
                   LEFT JOIN user_settings s ON s.user_id = u.id
                   WHERE u.id = %s""",
                (current_user["user_id"],)
            )
            result = cursor.fetchone()
            
            if not result:
                raise HTTPException(status_code=404, detail="User not found")
            
            return {
                "id": result["id"],
                "email": result["email"],
                "name": result["name"],
                "cefr_level": result["cefr_level"],
                "xp_total": result["xp_total"] or 0,
                "current_streak": result["current_streak"] or 0,
                "member_since": result["created_at"].isoformat() if result["created_at"] else None,
                "settings": {
                    "daily_goal_minutes": result["daily_goal_minutes"] or 15,
                    "notifications_enabled": result["notifications_enabled"] if result["notifications_enabled"] is not None else True,
                    "study_days": result["study_days"] or ["monday", "tuesday", "wednesday", "thursday", "friday"],
                    "preferred_ai": result["preferred_ai"] or "openai"
                },
                "api_keys": {
                    "openai_configured": bool(result["openai_api_key"]),
                    "openai_masked": mask_api_key(decrypt_api_key(result["openai_api_key"])) if result["openai_api_key"] else None,
                    "gemini_configured": bool(result["gemini_api_key"]),
                    "gemini_masked": mask_api_key(decrypt_api_key(result["gemini_api_key"])) if result["gemini_api_key"] else None
                }
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get profile error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load profile")


@router.put("/profile")
async def update_profile(
    update: ProfileUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update user profile
    FR27: Allow profile updates
    """
    try:
        with get_db_cursor() as cursor:
            if update.name:
                cursor.execute(
                    "UPDATE users SET name = %s WHERE id = %s",
                    (update.name, current_user["user_id"])
                )
            
            # Update settings
            updates = []
            values = []
            
            if update.daily_goal_minutes is not None:
                updates.append("daily_goal_minutes = %s")
                values.append(update.daily_goal_minutes)
            
            if update.notifications_enabled is not None:
                updates.append("notifications_enabled = %s")
                values.append(update.notifications_enabled)
            
            if updates:
                values.append(current_user["user_id"])
                cursor.execute(
                    f"UPDATE user_settings SET {', '.join(updates)} WHERE user_id = %s",
                    tuple(values)
                )
            
            return {"success": True, "message": "Profile updated successfully"}
    except Exception as e:
        logger.error(f"Update profile error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update profile")


@router.put("/api-keys")
async def update_api_keys(
    update: APIKeyUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update AI API keys
    FR28: Allow API key configuration for AI features
    """
    try:
        with get_db_cursor() as cursor:
            updates = []
            values = []
            
            if update.openai_api_key is not None:
                if update.openai_api_key == "":
                    updates.append("openai_api_key = NULL")
                else:
                    updates.append("openai_api_key = %s")
                    values.append(encrypt_api_key(update.openai_api_key))
            
            if update.gemini_api_key is not None:
                if update.gemini_api_key == "":
                    updates.append("gemini_api_key = NULL")
                else:
                    updates.append("gemini_api_key = %s")
                    values.append(encrypt_api_key(update.gemini_api_key))
            
            if update.preferred_ai is not None:
                if update.preferred_ai in ["openai", "gemini"]:
                    updates.append("preferred_ai = %s")
                    values.append(update.preferred_ai)
            
            if updates:
                values.append(current_user["user_id"])
                cursor.execute(
                    f"UPDATE user_settings SET {', '.join(updates)} WHERE user_id = %s",
                    tuple(values)
                )
            
            return {
                "success": True,
                "message": "API keys updated successfully",
                "openai_configured": update.openai_api_key is not None and update.openai_api_key != "",
                "gemini_configured": update.gemini_api_key is not None and update.gemini_api_key != ""
            }
    except Exception as e:
        logger.error(f"Update API keys error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update API keys")


@router.post("/test-api-key")
async def test_api_key(
    provider: str,
    current_user: dict = Depends(get_current_user)
):
    """Test if an API key is working"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                "SELECT openai_api_key, gemini_api_key FROM user_settings WHERE user_id = %s",
                (current_user["user_id"],)
            )
            settings = cursor.fetchone()
            
            if not settings:
                return {"success": False, "error": "No settings found"}
            
            if provider == "openai":
                key = decrypt_api_key(settings["openai_api_key"]) if settings["openai_api_key"] else None
                if not key:
                    return {"success": False, "error": "OpenAI API key not configured"}
                
                # Test the key
                import openai
                try:
                    client = openai.OpenAI(api_key=key)
                    client.models.list()
                    return {"success": True, "message": "OpenAI API key is valid"}
                except Exception as e:
                    return {"success": False, "error": f"OpenAI API error: {str(e)}"}
            
            elif provider == "gemini":
                key = decrypt_api_key(settings["gemini_api_key"]) if settings["gemini_api_key"] else None
                if not key:
                    return {"success": False, "error": "Gemini API key not configured"}
                
                # Test the key
                import google.generativeai as genai
                try:
                    genai.configure(api_key=key)
                    model = genai.GenerativeModel('gemini-pro')
                    model.generate_content("Hello")
                    return {"success": True, "message": "Gemini API key is valid"}
                except Exception as e:
                    return {"success": False, "error": f"Gemini API error: {str(e)}"}
            
            return {"success": False, "error": "Invalid provider"}
    except Exception as e:
        logger.error(f"Test API key error: {e}")
        raise HTTPException(status_code=500, detail="Failed to test API key")


@router.delete("/api-key/{provider}")
async def delete_api_key(
    provider: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete an API key"""
    try:
        with get_db_cursor() as cursor:
            if provider == "openai":
                cursor.execute(
                    "UPDATE user_settings SET openai_api_key = NULL WHERE user_id = %s",
                    (current_user["user_id"],)
                )
            elif provider == "gemini":
                cursor.execute(
                    "UPDATE user_settings SET gemini_api_key = NULL WHERE user_id = %s",
                    (current_user["user_id"],)
                )
            else:
                raise HTTPException(status_code=400, detail="Invalid provider")
            
            return {"success": True, "message": f"{provider.title()} API key removed"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete API key error: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete API key")
