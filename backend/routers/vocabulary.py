"""
Vocabulary Router - UC11: Vocabulary Advisor
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime
import json
import logging

from utils.jwt_handler import get_current_user
from database import get_db_cursor
from services.ai_engine import AIAdaptiveEngine

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/advisor")
async def get_vocabulary_advisor(current_user: dict = Depends(get_current_user)):
    """
    Get personalized vocabulary list based on mistakes
    FR16: AI-generated vocabulary advisor list
    """
    try:
        with get_db_cursor() as cursor:
            # Get user's mistakes from vocabulary_lists table
            cursor.execute(
                """SELECT word, translation, mistake_count, mastered, created_at
                   FROM vocabulary_lists 
                   WHERE user_id = %s AND mastered = FALSE
                   ORDER BY mistake_count DESC, created_at DESC
                   LIMIT 20""",
                (current_user["user_id"],)
            )
            mistakes = cursor.fetchall()
            
            # Get mastered words
            cursor.execute(
                """SELECT word FROM vocabulary_lists 
                   WHERE user_id = %s AND mastered = TRUE""",
                (current_user["user_id"],)
            )
            mastered = [row["word"] for row in cursor.fetchall()]
            
            # Get user's level for context
            cursor.execute(
                "SELECT cefr_level FROM users WHERE id = %s",
                (current_user["user_id"],)
            )
            user = cursor.fetchone()
            
            # Generate recommendations
            word_list = []
            for mistake in mistakes:
                translation_data = {}
                try:
                    translation_data = json.loads(mistake["translation"]) if mistake["translation"] else {}
                except:
                    translation_data = {"meaning": mistake["translation"]}
                
                word_list.append({
                    "word": mistake["word"],
                    "mistake_count": mistake["mistake_count"],
                    "context": translation_data.get("question", ""),
                    "correct_answer": translation_data.get("correct_answer", ""),
                    "last_seen": mistake["created_at"].isoformat() if mistake["created_at"] else None
                })
            
            # Add suggested words based on level if list is short
            if len(word_list) < 10:
                suggested = _get_suggested_vocabulary(user["cefr_level"] or "A1", mastered)
                word_list.extend(suggested[:10 - len(word_list)])
            
            return {
                "user_level": user["cefr_level"],
                "words_to_review": len(word_list),
                "mastered_count": len(mastered),
                "vocabulary_list": word_list,
                "tip": "Review these words regularly to improve your vocabulary!"
            }
    except Exception as e:
        logger.error(f"Get vocabulary advisor error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load vocabulary advisor")


@router.post("/add")
async def add_vocabulary(
    word: str,
    translation: Optional[str] = None,
    context: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Add a word to user's vocabulary list"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                """INSERT INTO vocabulary_lists 
                   (user_id, word, translation, mistake_count, mastered, created_at)
                   VALUES (%s, %s, %s, 0, FALSE, %s)
                   ON DUPLICATE KEY UPDATE 
                   translation = COALESCE(VALUES(translation), translation)""",
                (
                    current_user["user_id"],
                    word.lower().strip(),
                    json.dumps({"meaning": translation, "context": context}),
                    datetime.now()
                )
            )
            
            return {"success": True, "message": f"Added '{word}' to your vocabulary list"}
    except Exception as e:
        logger.error(f"Add vocabulary error: {e}")
        raise HTTPException(status_code=500, detail="Failed to add word")


@router.post("/mark-mastered/{word}")
async def mark_word_mastered(
    word: str,
    current_user: dict = Depends(get_current_user)
):
    """Mark a word as mastered"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                """UPDATE vocabulary_lists 
                   SET mastered = TRUE 
                   WHERE user_id = %s AND word = %s""",
                (current_user["user_id"], word.lower().strip())
            )
            
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Word not found in your list")
            
            return {"success": True, "message": f"Marked '{word}' as mastered!"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Mark mastered error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update word")


@router.delete("/{word}")
async def remove_vocabulary(
    word: str,
    current_user: dict = Depends(get_current_user)
):
    """Remove a word from vocabulary list"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                """DELETE FROM vocabulary_lists 
                   WHERE user_id = %s AND word = %s""",
                (current_user["user_id"], word.lower().strip())
            )
            
            return {"success": True, "message": f"Removed '{word}' from your list"}
    except Exception as e:
        logger.error(f"Remove vocabulary error: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove word")


@router.get("/practice")
async def get_vocabulary_practice(current_user: dict = Depends(get_current_user)):
    """Get vocabulary practice questions"""
    try:
        with get_db_cursor() as cursor:
            # Get words to practice (not mastered, prioritize high mistake count)
            cursor.execute(
                """SELECT word, translation, mistake_count
                   FROM vocabulary_lists 
                   WHERE user_id = %s AND mastered = FALSE
                   ORDER BY mistake_count DESC, RAND()
                   LIMIT 10""",
                (current_user["user_id"],)
            )
            words = cursor.fetchall()
            
            if not words:
                return {
                    "message": "No words to practice! Complete more lessons to build your vocabulary list.",
                    "questions": []
                }
            
            # Generate practice questions
            questions = []
            for word in words:
                translation_data = {}
                try:
                    translation_data = json.loads(word["translation"]) if word["translation"] else {}
                except:
                    pass
                
                questions.append({
                    "type": "vocabulary_recall",
                    "word": word["word"],
                    "hint": translation_data.get("context", ""),
                    "correct_answer": translation_data.get("correct_answer", translation_data.get("meaning", ""))
                })
            
            return {
                "total_words": len(questions),
                "questions": questions
            }
    except Exception as e:
        logger.error(f"Get vocabulary practice error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load practice")


def _get_suggested_vocabulary(level: str, mastered: List[str]) -> List[dict]:
    """Get suggested vocabulary words for a level"""
    vocabulary_by_level = {
        "A1": [
            {"word": "hello", "suggestion": True, "meaning": "greeting"},
            {"word": "goodbye", "suggestion": True, "meaning": "farewell"},
            {"word": "please", "suggestion": True, "meaning": "polite request"},
            {"word": "thank you", "suggestion": True, "meaning": "expression of gratitude"},
            {"word": "water", "suggestion": True, "meaning": "liquid for drinking"},
            {"word": "food", "suggestion": True, "meaning": "something to eat"},
            {"word": "house", "suggestion": True, "meaning": "place to live"},
            {"word": "family", "suggestion": True, "meaning": "relatives"},
            {"word": "friend", "suggestion": True, "meaning": "close companion"},
            {"word": "work", "suggestion": True, "meaning": "job or employment"}
        ],
        "A2": [
            {"word": "appointment", "suggestion": True, "meaning": "scheduled meeting"},
            {"word": "experience", "suggestion": True, "meaning": "knowledge from doing"},
            {"word": "opportunity", "suggestion": True, "meaning": "favorable chance"},
            {"word": "suggest", "suggestion": True, "meaning": "propose an idea"},
            {"word": "improve", "suggestion": True, "meaning": "make better"}
        ],
        "B1": [
            {"word": "accomplish", "suggestion": True, "meaning": "achieve or complete"},
            {"word": "consequence", "suggestion": True, "meaning": "result of an action"},
            {"word": "efficient", "suggestion": True, "meaning": "working well"},
            {"word": "inevitable", "suggestion": True, "meaning": "certain to happen"},
            {"word": "perspective", "suggestion": True, "meaning": "point of view"}
        ],
        "B2": [
            {"word": "ambiguous", "suggestion": True, "meaning": "having multiple meanings"},
            {"word": "comprehensive", "suggestion": True, "meaning": "complete and thorough"},
            {"word": "deteriorate", "suggestion": True, "meaning": "become worse"},
            {"word": "elaborate", "suggestion": True, "meaning": "detailed and complex"},
            {"word": "fluctuate", "suggestion": True, "meaning": "vary irregularly"}
        ],
        "C1": [
            {"word": "ubiquitous", "suggestion": True, "meaning": "present everywhere"},
            {"word": "pragmatic", "suggestion": True, "meaning": "practical approach"},
            {"word": "nuance", "suggestion": True, "meaning": "subtle difference"},
            {"word": "meticulous", "suggestion": True, "meaning": "very careful and precise"},
            {"word": "eloquent", "suggestion": True, "meaning": "fluent and persuasive"}
        ]
    }
    
    suggested = vocabulary_by_level.get(level, vocabulary_by_level["A1"])
    return [w for w in suggested if w["word"] not in mastered]
