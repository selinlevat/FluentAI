"""
Study Planner Router - UC13, UC18: Smart Reminder and Study Planner
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, time
import json
import logging

from utils.jwt_handler import get_current_user
from database import get_db_cursor

router = APIRouter()
logger = logging.getLogger(__name__)


class StudyPlanUpdate(BaseModel):
    daily_goal_minutes: Optional[int] = None
    study_days: Optional[List[str]] = None
    focus_skills: Optional[List[str]] = None
    reminder_time: Optional[str] = None
    notifications_enabled: Optional[bool] = None


@router.get("")
async def get_study_plan(current_user: dict = Depends(get_current_user)):
    """
    Get user's study plan
    FR23: Customizable daily goals
    FR29: Study planner functionality
    """
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                """SELECT daily_goal_minutes, study_days, notifications_enabled,
                          preferred_ai
                   FROM user_settings WHERE user_id = %s""",
                (current_user["user_id"],)
            )
            settings = cursor.fetchone()
            
            cursor.execute(
                "SELECT cefr_level FROM users WHERE id = %s",
                (current_user["user_id"],)
            )
            user = cursor.fetchone()
            
            study_days = ["monday", "tuesday", "wednesday", "thursday", "friday"]
            if settings and settings["study_days"]:
                try:
                    study_days = json.loads(settings["study_days"]) if isinstance(settings["study_days"], str) else settings["study_days"]
                except:
                    pass
            
            # Generate recommended focus skills based on performance (MariaDB compatible)
            cursor.execute(
                """SELECT answers FROM user_progress WHERE user_id = %s""",
                (current_user["user_id"],)
            )
            progress_rows = cursor.fetchall()
            
            # Process answers in Python to get skill stats
            skill_stats = {}
            for row in progress_rows:
                if row["answers"]:
                    try:
                        answers = json.loads(row["answers"]) if isinstance(row["answers"], str) else row["answers"]
                        if isinstance(answers, list):
                            for answer in answers:
                                if isinstance(answer, dict):
                                    skill = answer.get("skill_tag")
                                    is_correct = answer.get("is_correct", False)
                                    if skill:
                                        if skill not in skill_stats:
                                            skill_stats[skill] = {"total": 0, "correct": 0}
                                        skill_stats[skill]["total"] += 1
                                        if is_correct:
                                            skill_stats[skill]["correct"] += 1
                    except (json.JSONDecodeError, TypeError):
                        pass
            
            weak_skills = []
            for skill, stats in skill_stats.items():
                if stats["total"] > 0:
                    accuracy = (stats["correct"] / stats["total"]) * 100
                    if accuracy < 70:
                        weak_skills.append(skill)
            
            return {
                "daily_goal_minutes": settings["daily_goal_minutes"] if settings else 15,
                "study_days": study_days,
                "notifications_enabled": settings["notifications_enabled"] if settings else True,
                "current_level": user["cefr_level"] if user else "A1",
                "recommended_focus": weak_skills[:3] if weak_skills else ["vocabulary", "grammar"],
                "suggested_schedule": _generate_suggested_schedule(study_days),
                "tips": [
                    "Consistency is key! Try to study at the same time each day.",
                    "Short, frequent sessions are more effective than long, rare ones.",
                    "Practice speaking even if it feels uncomfortable at first."
                ]
            }
    except Exception as e:
        logger.error(f"Get study plan error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load study plan")


@router.put("")
async def update_study_plan(
    update: StudyPlanUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update study plan settings"""
    try:
        with get_db_cursor() as cursor:
            updates = []
            values = []
            
            if update.daily_goal_minutes is not None:
                updates.append("daily_goal_minutes = %s")
                values.append(update.daily_goal_minutes)
            
            if update.study_days is not None:
                updates.append("study_days = %s")
                values.append(json.dumps(update.study_days))
            
            if update.notifications_enabled is not None:
                updates.append("notifications_enabled = %s")
                values.append(update.notifications_enabled)
            
            if updates:
                values.append(current_user["user_id"])
                cursor.execute(
                    f"UPDATE user_settings SET {', '.join(updates)} WHERE user_id = %s",
                    tuple(values)
                )
            
            return {"success": True, "message": "Study plan updated"}
    except Exception as e:
        logger.error(f"Update study plan error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update study plan")


@router.get("/reminder-status")
async def get_reminder_status(current_user: dict = Depends(get_current_user)):
    """
    Get smart reminder status
    FR18: Smart reminder system
    FR35: Reminder notifications
    """
    try:
        with get_db_cursor() as cursor:
            # Check today's activity
            cursor.execute(
                """SELECT COUNT(*) as lessons_today,
                          COALESCE(SUM(xp_earned), 0) as xp_today
                   FROM user_progress
                   WHERE user_id = %s AND DATE(completed_at) = CURDATE()""",
                (current_user["user_id"],)
            )
            today = cursor.fetchone()
            
            # Get streak info
            cursor.execute(
                "SELECT current_streak FROM users WHERE id = %s",
                (current_user["user_id"],)
            )
            user = cursor.fetchone()
            
            # Get settings
            cursor.execute(
                "SELECT daily_goal_minutes, notifications_enabled FROM user_settings WHERE user_id = %s",
                (current_user["user_id"],)
            )
            settings = cursor.fetchone()
            
            goal_met = (today["xp_today"] or 0) >= 50
            
            reminder_message = None
            if not goal_met:
                streak = user["current_streak"] or 0
                if streak > 0:
                    reminder_message = f"Don't break your {streak}-day streak! Complete today's lesson."
                else:
                    reminder_message = "Start your learning journey today!"
            
            return {
                "goal_met_today": goal_met,
                "xp_earned_today": today["xp_today"] or 0,
                "lessons_completed_today": today["lessons_today"] or 0,
                "current_streak": user["current_streak"] or 0,
                "streak_at_risk": not goal_met and (user["current_streak"] or 0) > 0,
                "reminder_message": reminder_message,
                "notifications_enabled": settings["notifications_enabled"] if settings else True
            }
    except Exception as e:
        logger.error(f"Get reminder status error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get reminder status")


def _generate_suggested_schedule(study_days: List[str]) -> List[dict]:
    """Generate a suggested weekly schedule"""
    day_activities = {
        "monday": {"focus": "Daily Lesson + Grammar Sprint", "duration": 15},
        "tuesday": {"focus": "Daily Lesson + Vocabulary", "duration": 15},
        "wednesday": {"focus": "Speaking Practice (Prepare Me)", "duration": 20},
        "thursday": {"focus": "Daily Lesson + Word Sprint", "duration": 15},
        "friday": {"focus": "Review Mode + Free Talk", "duration": 25},
        "saturday": {"focus": "Speaking Practice", "duration": 20},
        "sunday": {"focus": "Weekly Review", "duration": 15}
    }
    
    schedule = []
    for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
        if day in study_days:
            schedule.append({
                "day": day.capitalize(),
                "active": True,
                **day_activities.get(day, {"focus": "Daily Lesson", "duration": 15})
            })
        else:
            schedule.append({
                "day": day.capitalize(),
                "active": False,
                "focus": "Rest day",
                "duration": 0
            })
    
    return schedule
