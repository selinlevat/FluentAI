"""
Admin Router - UC19, UC20: Statistics and Content Management
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime, date, timedelta
import json
import logging

from utils.jwt_handler import get_current_user, get_admin_user
from database import get_db_cursor

router = APIRouter()
logger = logging.getLogger(__name__)


class ContentCreate(BaseModel):
    type: str  # lesson_pack, lesson, question
    data: dict


class ContentUpdate(BaseModel):
    data: dict


@router.get("/stats")
async def get_admin_stats(current_user: dict = Depends(get_admin_user)):
    """
    Get system statistics for admin
    FR37: Admin statistics dashboard
    """
    try:
        with get_db_cursor() as cursor:
            # Total users
            cursor.execute("SELECT COUNT(*) as count FROM users")
            total_users = cursor.fetchone()["count"]
            
            # Active users (last 7 days)
            cursor.execute(
                """SELECT COUNT(DISTINCT user_id) as count 
                   FROM user_progress 
                   WHERE completed_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)"""
            )
            active_users = cursor.fetchone()["count"]
            
            # New users (last 7 days)
            cursor.execute(
                """SELECT COUNT(*) as count FROM users 
                   WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)"""
            )
            new_users = cursor.fetchone()["count"]
            
            # User levels distribution
            cursor.execute(
                """SELECT cefr_level, COUNT(*) as count 
                   FROM users 
                   GROUP BY cefr_level"""
            )
            level_distribution = {row["cefr_level"] or "Unassessed": row["count"] 
                                 for row in cursor.fetchall()}
            
            # Total lessons completed
            cursor.execute("SELECT COUNT(*) as count FROM user_progress")
            total_lessons = cursor.fetchone()["count"]
            
            # Average score
            cursor.execute("SELECT AVG(score) as avg FROM user_progress")
            avg_score = cursor.fetchone()["avg"] or 0
            
            # Content stats
            cursor.execute("SELECT COUNT(*) as count FROM lesson_packs")
            lesson_packs = cursor.fetchone()["count"]
            
            cursor.execute("SELECT COUNT(*) as count FROM lessons")
            lessons = cursor.fetchone()["count"]
            
            cursor.execute("SELECT COUNT(*) as count FROM questions")
            questions = cursor.fetchone()["count"]
            
            # Daily activity (last 7 days)
            daily_activity = []
            for i in range(7):
                day_date = date.today() - timedelta(days=6-i)
                cursor.execute(
                    """SELECT COUNT(*) as lessons, 
                              COUNT(DISTINCT user_id) as users
                       FROM user_progress 
                       WHERE DATE(completed_at) = %s""",
                    (day_date,)
                )
                day_stats = cursor.fetchone()
                daily_activity.append({
                    "date": day_date.isoformat(),
                    "lessons": day_stats["lessons"] or 0,
                    "users": day_stats["users"] or 0
                })
            
            return {
                "users": {
                    "total": total_users,
                    "active_7d": active_users,
                    "new_7d": new_users,
                    "level_distribution": level_distribution
                },
                "learning": {
                    "total_lessons_completed": total_lessons,
                    "average_score": round(avg_score, 1)
                },
                "content": {
                    "lesson_packs": lesson_packs,
                    "lessons": lessons,
                    "questions": questions
                },
                "daily_activity": daily_activity,
                "generated_at": datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"Get admin stats error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load statistics")


@router.get("/content")
async def get_content(
    content_type: Optional[str] = None,
    current_user: dict = Depends(get_admin_user)
):
    """
    Get content for management
    FR38: Content management functionality
    """
    try:
        with get_db_cursor() as cursor:
            result = {"lesson_packs": [], "lessons": [], "questions": []}
            
            if content_type in [None, "lesson_packs"]:
                cursor.execute(
                    """SELECT id, title, description, cefr_level, order_index, icon
                       FROM lesson_packs ORDER BY order_index"""
                )
                result["lesson_packs"] = cursor.fetchall()
            
            if content_type in [None, "lessons"]:
                cursor.execute(
                    """SELECT l.id, l.pack_id, l.title, l.description, l.type,
                              l.cefr_level, l.xp_reward, l.order_index,
                              lp.title as pack_title
                       FROM lessons l
                       LEFT JOIN lesson_packs lp ON l.pack_id = lp.id
                       ORDER BY l.pack_id, l.order_index"""
                )
                result["lessons"] = cursor.fetchall()
            
            if content_type in [None, "questions"]:
                cursor.execute(
                    """SELECT q.id, q.lesson_id, q.type, q.content, 
                              q.correct_answer, q.skill_tag, q.difficulty,
                              l.title as lesson_title
                       FROM questions q
                       LEFT JOIN lessons l ON q.lesson_id = l.id
                       ORDER BY q.lesson_id, q.id
                       LIMIT 100"""
                )
                questions = cursor.fetchall()
                for q in questions:
                    if isinstance(q["content"], str):
                        q["content"] = json.loads(q["content"])
                result["questions"] = questions
            
            return result
    except Exception as e:
        logger.error(f"Get content error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load content")


@router.post("/content")
async def create_content(
    content: ContentCreate,
    current_user: dict = Depends(get_admin_user)
):
    """Create new content"""
    try:
        with get_db_cursor() as cursor:
            if content.type == "lesson_pack":
                cursor.execute(
                    """INSERT INTO lesson_packs 
                       (title, description, cefr_level, order_index, icon)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (
                        content.data.get("title"),
                        content.data.get("description"),
                        content.data.get("cefr_level", "A1"),
                        content.data.get("order_index", 0),
                        content.data.get("icon", "📚")
                    )
                )
                return {"success": True, "id": cursor.lastrowid, "type": "lesson_pack"}
            
            elif content.type == "lesson":
                cursor.execute(
                    """INSERT INTO lessons 
                       (pack_id, title, description, type, cefr_level, xp_reward, order_index)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (
                        content.data.get("pack_id"),
                        content.data.get("title"),
                        content.data.get("description"),
                        content.data.get("type", "daily"),
                        content.data.get("cefr_level", "A1"),
                        content.data.get("xp_reward", 50),
                        content.data.get("order_index", 0)
                    )
                )
                return {"success": True, "id": cursor.lastrowid, "type": "lesson"}
            
            elif content.type == "question":
                cursor.execute(
                    """INSERT INTO questions 
                       (lesson_id, type, content, correct_answer, skill_tag, difficulty, xp_value)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (
                        content.data.get("lesson_id"),
                        content.data.get("type", "mcq"),
                        json.dumps(content.data.get("content", {})),
                        json.dumps(content.data.get("correct_answer")),
                        content.data.get("skill_tag", "grammar"),
                        content.data.get("difficulty", 1),
                        content.data.get("xp_value", 10)
                    )
                )
                return {"success": True, "id": cursor.lastrowid, "type": "question"}
            
            raise HTTPException(status_code=400, detail="Invalid content type")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create content error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create content")


@router.put("/content/{content_type}/{content_id}")
async def update_content(
    content_type: str,
    content_id: int,
    update: ContentUpdate,
    current_user: dict = Depends(get_admin_user)
):
    """Update existing content"""
    try:
        with get_db_cursor() as cursor:
            if content_type == "lesson_pack":
                cursor.execute(
                    """UPDATE lesson_packs 
                       SET title = %s, description = %s, cefr_level = %s, 
                           order_index = %s, icon = %s
                       WHERE id = %s""",
                    (
                        update.data.get("title"),
                        update.data.get("description"),
                        update.data.get("cefr_level"),
                        update.data.get("order_index"),
                        update.data.get("icon"),
                        content_id
                    )
                )
            elif content_type == "lesson":
                cursor.execute(
                    """UPDATE lessons 
                       SET title = %s, description = %s, type = %s,
                           cefr_level = %s, xp_reward = %s, order_index = %s
                       WHERE id = %s""",
                    (
                        update.data.get("title"),
                        update.data.get("description"),
                        update.data.get("type"),
                        update.data.get("cefr_level"),
                        update.data.get("xp_reward"),
                        update.data.get("order_index"),
                        content_id
                    )
                )
            elif content_type == "question":
                cursor.execute(
                    """UPDATE questions 
                       SET type = %s, content = %s, correct_answer = %s,
                           skill_tag = %s, difficulty = %s
                       WHERE id = %s""",
                    (
                        update.data.get("type"),
                        json.dumps(update.data.get("content", {})),
                        json.dumps(update.data.get("correct_answer")),
                        update.data.get("skill_tag"),
                        update.data.get("difficulty"),
                        content_id
                    )
                )
            else:
                raise HTTPException(status_code=400, detail="Invalid content type")
            
            return {"success": True, "message": "Content updated"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update content error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update content")


@router.delete("/content/{content_type}/{content_id}")
async def delete_content(
    content_type: str,
    content_id: int,
    current_user: dict = Depends(get_admin_user)
):
    """Delete content"""
    try:
        with get_db_cursor() as cursor:
            table_map = {
                "lesson_pack": "lesson_packs",
                "lesson": "lessons",
                "question": "questions"
            }
            
            if content_type not in table_map:
                raise HTTPException(status_code=400, detail="Invalid content type")
            
            cursor.execute(
                f"DELETE FROM {table_map[content_type]} WHERE id = %s",
                (content_id,)
            )
            
            return {"success": True, "message": "Content deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete content error: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete content")


@router.get("/users")
async def get_users(
    page: int = 1,
    limit: int = 20,
    current_user: dict = Depends(get_admin_user)
):
    """Get user list for admin"""
    try:
        with get_db_cursor() as cursor:
            offset = (page - 1) * limit
            
            cursor.execute("SELECT COUNT(*) as total FROM users")
            total = cursor.fetchone()["total"]
            
            cursor.execute(
                """SELECT id, email, name, cefr_level, xp_total, 
                          current_streak, created_at, last_login, role
                   FROM users
                   ORDER BY created_at DESC
                   LIMIT %s OFFSET %s""",
                (limit, offset)
            )
            users = cursor.fetchall()
            
            return {
                "users": [
                    {
                        **u,
                        "created_at": u["created_at"].isoformat() if u["created_at"] else None,
                        "last_login": u["last_login"].isoformat() if u["last_login"] else None
                    }
                    for u in users
                ],
                "total": total,
                "page": page,
                "pages": (total + limit - 1) // limit
            }
    except Exception as e:
        logger.error(f"Get users error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load users")
