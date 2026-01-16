"""
Lessons Router - UC4, UC5, UC6, UC7, UC8: Daily Lessons, Grammar Sprint, Word Sprint, Lesson Packs
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import datetime, date
import json
import logging

from utils.jwt_handler import get_current_user
from database import get_db_cursor
from services.xp_calculator import XPCalculator
from services.achievement_service import AchievementService
from services.achievement_service import AchievementService
from services.ai_engine import AIAdaptiveEngine
from models.lesson import LessonSubmission, LessonResult, AnswerSubmission

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/daily/cards")
async def get_daily_cards(current_user: dict = Depends(get_current_user)):
    """
    Get daily lesson info cards
    """
    try:
        with get_db_cursor() as cursor:
            # Get user's level
            cursor.execute(
                "SELECT cefr_level FROM users WHERE id = %s",
                (current_user["user_id"],)
            )
            user = cursor.fetchone()
            user_level = user["cefr_level"] or "A1"
            
            # Fetch 15 cards for the user's level
            cursor.execute(
                """SELECT id, title, content, example 
                   FROM daily_lesson_cards 
                   WHERE cefr_level = %s 
                   ORDER BY sort_order ASC, id ASC
                   LIMIT 15""",
                (user_level,)
            )
            cards = cursor.fetchall()
            
            return {
                "user_level": user_level,
                "total_cards": len(cards),
                "cards": [
                    {
                        "id": c["id"],
                        "title": c["title"],
                        "content": c["content"],
                        "example": c["example"]
                    }
                    for c in cards
                ]
            }
    except Exception as e:
        logger.error(f"Get daily cards error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load daily cards")


@router.get("/daily")
async def get_daily_lesson(current_user: dict = Depends(get_current_user)):
    """
    Get today's daily lesson
    FR4: Assign and display trackable daily goals
    FR5: Present 10-question core lesson
    """
    try:
        with get_db_cursor() as cursor:
            # Get user's level
            cursor.execute(
                "SELECT cefr_level, xp_total FROM users WHERE id = %s",
                (current_user["user_id"],)
            )
            user = cursor.fetchone()
            user_level = user["cefr_level"] or "A1"
            
            # Check if daily lesson already completed today
            cursor.execute(
                """SELECT id FROM user_progress 
                   WHERE user_id = %s 
                   AND DATE(completed_at) = CURDATE()
                   AND lesson_id IN (SELECT id FROM lessons WHERE type = 'daily')""",
                (current_user["user_id"],)
            )
            completed_today = cursor.fetchone()
            
            # Get daily lesson for user's level
            cursor.execute(
                """SELECT l.id, l.title, l.description, l.xp_reward, l.questions_count
                   FROM lessons l
                   WHERE l.type = 'daily' AND l.cefr_level = %s
                   ORDER BY RAND() LIMIT 1""",
                (user_level,)
            )
            lesson = cursor.fetchone()
            
            if not lesson:
                # Try to get any daily lesson regardless of level
                cursor.execute(
                    """SELECT l.id, l.title, l.description, l.xp_reward, l.questions_count
                       FROM lessons l
                       WHERE l.type = 'daily'
                       ORDER BY RAND() LIMIT 1"""
                )
                lesson = cursor.fetchone()
            
            if not lesson:
                return {
                    "lesson_id": 0,
                    "title": "No Lessons Available",
                    "description": "Please add lessons to the database.",
                    "xp_reward": 0,
                    "completed_today": False,
                    "user_level": user_level,
                    "questions": []
                }
            
            # Get questions with correct_answer from database
            cursor.execute(
                """SELECT id, type, content, correct_answer, skill_tag, xp_value
                   FROM questions WHERE lesson_id = %s
                   ORDER BY RAND() LIMIT 10""",
                (lesson["id"],)
            )
            questions = cursor.fetchall()
            
            return {
                "lesson_id": lesson["id"],
                "title": lesson["title"] or "Daily Practice",
                "description": lesson["description"],
                "xp_reward": lesson["xp_reward"],
                "completed_today": completed_today is not None,
                "user_level": user_level,
                "questions": [
                    {
                        "id": q["id"],
                        "type": q["type"],
                        "skill_tag": q["skill_tag"],
                        "xp_value": q["xp_value"],
                        "correct_answer": json.loads(q["correct_answer"]) if isinstance(q["correct_answer"], str) else q["correct_answer"],
                        **(q["content"] if isinstance(q["content"], dict) else json.loads(q["content"]))
                    }
                    for q in questions
                ]
            }
    except Exception as e:
        logger.error(f"Get daily lesson error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load daily lesson")


@router.get("/grammar-sprint")
async def get_grammar_sprint(current_user: dict = Depends(get_current_user)):
    """
    Get Grammar Sprint lesson (20 questions, time-limited)
    FR6: Time-constrained grammar test with 20-second timer
    """
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                "SELECT cefr_level FROM users WHERE id = %s",
                (current_user["user_id"],)
            )
            user = cursor.fetchone()
            user_level = user["cefr_level"] or "A1"
            
            # Get grammar sprint lesson
            # Determine difficulty range based on user level
            # A1/A2 -> Difficulty 1, 2
            # B1/B2 -> Difficulty 3, 4
            # C1/C2 -> Difficulty 5
            if user_level in ["A1", "A2"]:
                difficulty_sql = "difficulty IN (1, 2)"
            elif user_level in ["B1", "B2"]:
                difficulty_sql = "difficulty IN (3, 4)"
            else: # C1, C2
                difficulty_sql = "difficulty = 5"

            cursor.execute(
                "SELECT id FROM lessons WHERE type = 'grammar_sprint' LIMIT 1"
            )
            lesson = cursor.fetchone()
            lesson_id = lesson["id"] if lesson else 0
            
            # Fetch 20 random questions for the user's level
            cursor.execute(
                f"""SELECT id, type, content, correct_answer, xp_value
                   FROM questions 
                   WHERE skill_tag = 'grammar' AND {difficulty_sql}
                   ORDER BY RAND() LIMIT 20"""
            )
            questions = cursor.fetchall()

            # Fallback: if not enough questions for specific level, try wider range
            if len(questions) < 5:
                 cursor.execute(
                    """SELECT id, type, content, correct_answer, xp_value
                       FROM questions 
                       WHERE skill_tag = 'grammar'
                       ORDER BY RAND() LIMIT 20"""
                )
                 questions = cursor.fetchall()
            
            if not questions:
                return {
                    "lesson_id": 0,
                    "title": "Grammar Sprint",
                    "description": "No grammar questions available.",
                    "questions": []
                }
            
            return {
                "lesson_id": lesson_id,
                "title": "Grammar Sprint",
                "description": "Answer 20 grammar questions. You have 20 seconds per question!",
                "time_per_question": 20,
                "total_questions": len(questions),
                "xp_reward": 30,
                "user_level": user_level,
                "questions": [
                    {
                        "id": q["id"],
                        "type": q["type"],
                        "xp_value": q["xp_value"],
                        "correct_answer": json.loads(q["correct_answer"]) if isinstance(q["correct_answer"], str) else q["correct_answer"],
                        **(q["content"] if isinstance(q["content"], dict) else json.loads(q["content"]))
                    }
                    for q in questions
                ]
            }
    except Exception as e:
        logger.error(f"Get grammar sprint error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load grammar sprint")


@router.get("/word-sprint")
async def get_word_sprint(current_user: dict = Depends(get_current_user)):
    """
    Get Word Sprint+ lesson (vocabulary mini-game)
    FR7: 30-second mini-game for vocabulary
    """
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                "SELECT cefr_level FROM users WHERE id = %s",
                (current_user["user_id"],)
            )
            user = cursor.fetchone()
            user_level = user["cefr_level"] or "A1"
            
            # Determine difficulty range based on user level
            if user_level in ["A1", "A2"]:
                difficulty_sql = "difficulty IN (1, 2)"
            elif user_level in ["B1", "B2"]:
                difficulty_sql = "difficulty IN (3, 4)"
            else: # C1, C2
                difficulty_sql = "difficulty = 5"

            # Get word sprint lesson
            cursor.execute(
                "SELECT id FROM lessons WHERE type = 'word_sprint' LIMIT 1"
            )
            lesson = cursor.fetchone()
            lesson_id = lesson["id"] if lesson else 0
            
            # Fetch 20 random questions for the user's level
            cursor.execute(
                f"""SELECT id, type, content, correct_answer, xp_value
                   FROM questions 
                   WHERE skill_tag = 'vocabulary' AND {difficulty_sql}
                   ORDER BY RAND() LIMIT 20"""
            )
            questions = cursor.fetchall()

            # Fallback
            if len(questions) < 5:
                 cursor.execute(
                    """SELECT id, type, content, correct_answer, xp_value
                       FROM questions 
                       WHERE skill_tag = 'vocabulary'
                       ORDER BY RAND() LIMIT 20"""
                )
                 questions = cursor.fetchall()
            
            if not questions:
                return {
                    "lesson_id": 0,
                    "title": "Word Sprint+",
                    "description": "No vocabulary questions available.",
                    "questions": []
                }
            
            return {
                "lesson_id": lesson_id,
                "title": "Word Sprint+",
                "description": "Vocabulary challenge! You have 30 seconds per question!",
                "time_per_question": 30,
                "total_questions": len(questions),
                "xp_reward": 25,
                "user_level": user_level,
                "questions": [
                    {
                        "id": q["id"],
                        "type": q["type"],
                        "xp_value": q["xp_value"],
                        "correct_answer": json.loads(q["correct_answer"]) if isinstance(q["correct_answer"], str) else q["correct_answer"],
                        **(q["content"] if isinstance(q["content"], dict) else json.loads(q["content"]))
                    }
                    for q in questions
                ]
            }
    except Exception as e:
        logger.error(f"Get word sprint error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load word sprint")


@router.get("/packs")
async def get_lesson_packs(current_user: dict = Depends(get_current_user)):
    """
    Get all lesson packs with progress
    FR10: Provide structured lesson packs
    """
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                "SELECT cefr_level FROM users WHERE id = %s",
                (current_user["user_id"],)
            )
            user = cursor.fetchone()
            user_level = user["cefr_level"] or "A1"
            
            cursor.execute(
                """SELECT lp.id, lp.title, lp.description, lp.cefr_level, 
                          lp.order_index, lp.icon,
                          COUNT(DISTINCT l.id) as total_lessons,
                          COUNT(DISTINCT up.lesson_id) as completed_lessons
                   FROM lesson_packs lp
                   LEFT JOIN lessons l ON l.pack_id = lp.id
                   LEFT JOIN user_progress up ON up.lesson_id = l.id 
                        AND up.user_id = %s
                   GROUP BY lp.id
                   ORDER BY lp.order_index""",
                (current_user["user_id"],)
            )
            packs = cursor.fetchall()
            
            if not packs:
                packs = _get_sample_lesson_packs(user_level)
            else:
                # Determine which packs are unlocked
                level_order = ["A1", "A2", "B1", "B2", "C1", "C2"]
                user_level_index = level_order.index(user_level)
                
                packs = [
                    {
                        "id": p["id"],
                        "title": p["title"],
                        "description": p["description"],
                        "cefr_level": p["cefr_level"],
                        "total_lessons": p["total_lessons"],
                        "completed_lessons": p["completed_lessons"],
                        "progress_percent": int((p["completed_lessons"] / p["total_lessons"]) * 100) if p["total_lessons"] > 0 else 0,
                        "is_locked": level_order.index(p["cefr_level"]) > user_level_index,
                        "icon": p["icon"] or "📚"
                    }
                    for p in packs
                ]
            
            return {"packs": packs, "user_level": user_level}
    except Exception as e:
        logger.error(f"Get lesson packs error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load lesson packs")


@router.get("/packs/{pack_id}")
async def get_pack_lessons(
    pack_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Get lessons within a specific pack"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                """SELECT l.id, l.title, l.description, l.xp_reward, l.order_index,
                          up.score, up.completed_at
                   FROM lessons l
                   LEFT JOIN user_progress up ON up.lesson_id = l.id 
                        AND up.user_id = %s
                   WHERE l.pack_id = %s
                   ORDER BY l.order_index""",
                (current_user["user_id"], pack_id)
            )
            lessons = cursor.fetchall()
            
            return {
                "pack_id": pack_id,
                "lessons": [
                    {
                        "id": l["id"],
                        "title": l["title"],
                        "description": l["description"],
                        "xp_reward": l["xp_reward"],
                        "completed": l["completed_at"] is not None,
                        "score": l["score"],
                        "order": l["order_index"]
                    }
                    for l in lessons
                ]
            }
    except Exception as e:
        logger.error(f"Get pack lessons error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load pack lessons")


@router.get("/{lesson_id}/questions")
async def get_lesson_questions(
    lesson_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Get questions for a specific lesson"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                """SELECT l.id, l.title, l.type, l.xp_reward, l.cefr_level
                   FROM lessons l WHERE l.id = %s""",
                (lesson_id,)
            )
            lesson = cursor.fetchone()
            
            if not lesson:
                raise HTTPException(status_code=404, detail="Lesson not found")
            
            cursor.execute(
                """SELECT id, type, content, skill_tag, xp_value
                   FROM questions WHERE lesson_id = %s
                   ORDER BY RAND()""",
                (lesson_id,)
            )
            questions = cursor.fetchall()
            
            return {
                "lesson_id": lesson["id"],
                "title": lesson["title"],
                "type": lesson["type"],
                "xp_reward": lesson["xp_reward"],
                "cefr_level": lesson["cefr_level"],
                "questions": [
                    {
                        "id": q["id"],
                        "type": q["type"],
                        "skill_tag": q["skill_tag"],
                        "xp_value": q["xp_value"],
                        **(q["content"] if isinstance(q["content"], dict) else json.loads(q["content"]))
                    }
                    for q in questions
                ]
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get lesson questions error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load questions")


@router.post("/{lesson_id}/submit")
async def submit_lesson(
    lesson_id: int,
    submission: LessonSubmission,
    current_user: dict = Depends(get_current_user)
):
    """
    Submit lesson answers and get results
    FR8, FR9: Multiple choice, matching, gap-fill questions with scoring
    """
    try:
        with get_db_cursor() as cursor:
            # Get user data
            cursor.execute(
                "SELECT cefr_level, xp_total, current_streak, longest_streak FROM users WHERE id = %s",
                (current_user["user_id"],)
            )
            user = cursor.fetchone()
            
            # Process answers
            results = []
            correct_count = 0
            mistakes = []
            
            for answer in submission.answers:
                # Always get question from database
                cursor.execute(
                    "SELECT correct_answer, skill_tag, content FROM questions WHERE id = %s",
                    (answer.question_id,)
                )
                question = cursor.fetchone()
                
                if not question:
                    # Question not found in database, skip
                    logger.warning(f"Question {answer.question_id} not found in database")
                    continue
                
                # Get correct answer from database
                correct_answer = question["correct_answer"]
                if isinstance(correct_answer, str):
                    try:
                        correct_answer = json.loads(correct_answer)
                    except:
                        pass
                
                skill_tag = question["skill_tag"]
                content = question["content"] if isinstance(question["content"], dict) else json.loads(question["content"])
                question_text = content.get("question", "") or content.get("sentence", "")
                
                user_ans = str(answer.user_answer).lower().strip()
                correct_ans = str(correct_answer).lower().strip()
                is_correct = user_ans == correct_ans
                
                if is_correct:
                    correct_count += 1
                else:
                    mistakes.append({
                        "question_id": answer.question_id,
                        "your_answer": answer.user_answer,
                        "correct_answer": correct_answer,
                        "skill_tag": skill_tag,
                        "question": question_text
                    })
                
                results.append({
                    "question_id": answer.question_id,
                    "is_correct": is_correct,
                    "skill_tag": skill_tag
                })
            
            total_questions = len(submission.answers)
            score = int((correct_count / total_questions) * 100) if total_questions > 0 else 0
            
            # Calculate XP
            xp_data = XPCalculator.calculate_lesson_xp(
                correct_count,
                total_questions,
                user["current_streak"] or 0,
                "daily"
            )
            
            # Update streak
            cursor.execute(
                """SELECT DATE(MAX(completed_at)) as last_date 
                   FROM user_progress WHERE user_id = %s""",
                (current_user["user_id"],)
            )
            last_progress = cursor.fetchone()
            
            new_streak = user["current_streak"] or 0
            if last_progress and last_progress["last_date"]:
                days_diff = (date.today() - last_progress["last_date"]).days
                if days_diff == 1:
                    new_streak += 1
                elif days_diff > 1:
                    new_streak = 1
            else:
                new_streak = 1
            
            # Check for level up
            old_xp = user["xp_total"] or 0
            new_xp = old_xp + xp_data["xp_total"]
            level_up, old_level, new_level = XPCalculator.check_level_up(old_xp, new_xp)
            
            # Update user
            longest_streak = max(user["longest_streak"] or 0, new_streak)
            
            # Determine new level - update if level_up occurred
            final_level = new_level if level_up else (user["cefr_level"] or "A1")
            
            cursor.execute(
                """UPDATE users 
                   SET xp_total = %s, current_streak = %s, longest_streak = %s,
                       cefr_level = %s
                   WHERE id = %s""",
                (new_xp, new_streak, longest_streak, final_level, current_user["user_id"])
            )
            
            # Save progress
            cursor.execute(
                """INSERT INTO user_progress 
                   (user_id, lesson_id, score, xp_earned, answers, completed_at, time_spent_seconds)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (
                    current_user["user_id"],
                    lesson_id,
                    score,
                    xp_data["xp_total"],
                    json.dumps(results),
                    datetime.now(),
                    submission.total_time_seconds
                )
            )
            
            # Get lesson type
            cursor.execute("SELECT type FROM lessons WHERE id = %s", (lesson_id,))
            lesson_record = cursor.fetchone()
            lesson_type = lesson_record["type"] if lesson_record else "lesson"
            
            # Save mistakes for review
            for mistake in mistakes:
                # Legacy support for vocabulary list
                cursor.execute(
                    """INSERT INTO vocabulary_lists 
                       (user_id, word, translation, mistake_count, mastered)
                       VALUES (%s, %s, %s, 1, FALSE)
                       ON DUPLICATE KEY UPDATE mistake_count = mistake_count + 1""",
                    (current_user["user_id"], mistake.get("question", "")[:100], json.dumps(mistake), )
                )
                
                # New System: Save to user_mistakes
                cursor.execute(
                    """INSERT INTO user_mistakes (user_id, question_id, source_type)
                       VALUES (%s, %s, %s)
                       ON DUPLICATE KEY UPDATE created_at = NOW()""",
                    (current_user["user_id"], mistake["question_id"], lesson_type)
                )
            
            # Trigger Achievement Check
            # Need total lessons count for 'first_lesson' check
            cursor.execute("SELECT COUNT(*) as count FROM user_progress WHERE user_id = %s", (current_user["user_id"],))
            total_lessons_count = cursor.fetchone()["count"]
            
            current_stats = {
                "xp_total": new_xp,
                "current_streak": new_streak,
                "total_lessons": total_lessons_count
            }
            
            activity_details = {
                "type": "lesson", # or specific type if available
                "score": score
            }
            
            new_achievements = AchievementService.check_achievements(
                cursor, 
                current_user["user_id"], 
                current_stats, 
                activity_details
            )

            return LessonResult(
                lesson_id=lesson_id,
                score=score,
                total_questions=total_questions,
                correct_count=correct_count,
                xp_earned=xp_data["xp_total"],
                streak_bonus=xp_data["xp_streak_bonus"],
                new_streak=new_streak,
                level_up=level_up,
                new_level=new_level if level_up else None,
                mistakes=mistakes,
                new_achievements=new_achievements
            )
    except Exception as e:
        logger.error(f"Submit lesson error: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit lesson")


def _generate_sample_daily_lesson(level: str, completed: bool):
    """Generate sample daily lesson"""
    return {
        "lesson_id": 0,
        "title": f"Daily Practice - {level}",
        "description": "Complete today's lesson to maintain your streak!",
        "xp_reward": 50,
        "completed_today": completed,
        "user_level": level,
        "questions": [
            {
                "id": 1, "type": "mcq", "skill_tag": "grammar", "xp_value": 10,
                "question": "She ___ to the store yesterday.",
                "options": ["go", "goes", "went", "going"],
                "correct_answer": "went"
            },
            {
                "id": 2, "type": "mcq", "skill_tag": "vocabulary", "xp_value": 10,
                "question": "What is the meaning of 'happy'?",
                "options": ["sad", "joyful", "angry", "tired"],
                "correct_answer": "joyful"
            },
            {
                "id": 3, "type": "gap_fill", "skill_tag": "grammar", "xp_value": 10,
                "sentence": "I have ___ living here for three years.",
                "options": ["be", "been", "being", "was"],
                "correct_answer": "been"
            },
            {
                "id": 4, "type": "mcq", "skill_tag": "vocabulary", "xp_value": 10,
                "question": "The opposite of 'big' is:",
                "options": ["large", "huge", "small", "giant"],
                "correct_answer": "small"
            },
            {
                "id": 5, "type": "mcq", "skill_tag": "grammar", "xp_value": 10,
                "question": "They ___ playing football when it started raining.",
                "options": ["was", "were", "are", "is"],
                "correct_answer": "were"
            },
            {
                "id": 6, "type": "translation", "skill_tag": "vocabulary", "xp_value": 10,
                "question": "Translate: 'Thank you very much'",
                "options": ["Çok teşekkürler", "Merhaba", "Günaydın", "İyi akşamlar"],
                "correct_answer": "Çok teşekkürler"
            },
            {
                "id": 7, "type": "mcq", "skill_tag": "grammar", "xp_value": 10,
                "question": "I ___ never seen such a beautiful place.",
                "options": ["has", "have", "had", "having"],
                "correct_answer": "have"
            },
            {
                "id": 8, "type": "mcq", "skill_tag": "vocabulary", "xp_value": 10,
                "question": "A person who writes books is called a(n):",
                "options": ["teacher", "author", "doctor", "engineer"],
                "correct_answer": "author"
            },
            {
                "id": 9, "type": "reorder", "skill_tag": "grammar", "xp_value": 10,
                "question": "Arrange the words: 'school / to / I / every / go / day'",
                "options": ["I go to school every day", "Every day I go to school", "To school I go every day", "Go I to school every day"],
                "correct_answer": "I go to school every day"
            },
            {
                "id": 10, "type": "mcq", "skill_tag": "grammar", "xp_value": 10,
                "question": "If I ___ you, I would study harder.",
                "options": ["am", "was", "were", "be"],
                "correct_answer": "were"
            }
        ]
    }


def _get_sample_grammar_questions(level: str):
    """Get sample grammar questions"""
    return [
        {"id": 1, "type": "mcq", "xp_value": 5, "question": "She ___ breakfast every morning.", "options": ["eat", "eats", "eating", "eaten"], "correct_answer": "eats"},
        {"id": 2, "type": "mcq", "xp_value": 5, "question": "They ___ to Paris last summer.", "options": ["go", "goes", "went", "going"], "correct_answer": "went"},
        {"id": 3, "type": "mcq", "xp_value": 5, "question": "I ___ reading when you called.", "options": ["am", "was", "were", "is"], "correct_answer": "was"},
        {"id": 4, "type": "mcq", "xp_value": 5, "question": "We have ___ here since 2010.", "options": ["live", "lived", "living", "lives"], "correct_answer": "lived"},
        {"id": 5, "type": "mcq", "xp_value": 5, "question": "___ you like some coffee?", "options": ["Do", "Would", "Are", "Is"], "correct_answer": "Would"},
    ]


def _get_sample_vocabulary_questions(level: str):
    """Get sample vocabulary questions"""
    return [
        {"id": 1, "type": "mcq", "xp_value": 5, "question": "Opposite of 'hot':", "options": ["warm", "cold", "cool", "freeze"], "correct_answer": "cold"},
        {"id": 2, "type": "mcq", "xp_value": 5, "question": "Synonym of 'fast':", "options": ["slow", "quick", "late", "early"], "correct_answer": "quick"},
        {"id": 3, "type": "mcq", "xp_value": 5, "question": "A place to buy medicine:", "options": ["bakery", "pharmacy", "library", "bank"], "correct_answer": "pharmacy"},
        {"id": 4, "type": "mcq", "xp_value": 5, "question": "The color of grass:", "options": ["blue", "red", "green", "yellow"], "correct_answer": "green"},
        {"id": 5, "type": "mcq", "xp_value": 5, "question": "Animal that barks:", "options": ["cat", "dog", "bird", "fish"], "correct_answer": "dog"},
    ]


def _get_sample_lesson_packs(level: str):
    """Get sample lesson packs"""
    level_order = ["A1", "A2", "B1", "B2", "C1", "C2"]
    user_index = level_order.index(level)
    
    packs = [
        {"id": 1, "title": "Basics 1", "description": "Start your English journey", "cefr_level": "A1", "total_lessons": 5, "completed_lessons": 0, "icon": "🌱"},
        {"id": 2, "title": "Greetings", "description": "Learn to say hello and goodbye", "cefr_level": "A1", "total_lessons": 5, "completed_lessons": 0, "icon": "👋"},
        {"id": 3, "title": "Family", "description": "Family members vocabulary", "cefr_level": "A1", "total_lessons": 5, "completed_lessons": 0, "icon": "👨‍👩‍👧‍👦"},
        {"id": 4, "title": "Food & Drinks", "description": "Ordering at restaurants", "cefr_level": "A2", "total_lessons": 6, "completed_lessons": 0, "icon": "🍕"},
        {"id": 5, "title": "Travel", "description": "Useful travel vocabulary", "cefr_level": "A2", "total_lessons": 6, "completed_lessons": 0, "icon": "✈️"},
        {"id": 6, "title": "Past Tense", "description": "Talk about the past", "cefr_level": "B1", "total_lessons": 7, "completed_lessons": 0, "icon": "⏰"},
        {"id": 7, "title": "Business English", "description": "Professional communication", "cefr_level": "B2", "total_lessons": 8, "completed_lessons": 0, "icon": "💼"},
        {"id": 8, "title": "Advanced Grammar", "description": "Complex structures", "cefr_level": "C1", "total_lessons": 10, "completed_lessons": 0, "icon": "📚"},
    ]
    
    for pack in packs:
        pack_index = level_order.index(pack["cefr_level"])
        pack["is_locked"] = pack_index > user_index
        pack["progress_percent"] = 0
    
    return packs
