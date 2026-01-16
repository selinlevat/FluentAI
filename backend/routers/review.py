"""
Review Router - UC12: Review Mode
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime
import json
import logging

from utils.jwt_handler import get_current_user
from database import get_db_cursor
from services.ai_engine import AIAdaptiveEngine
from services.xp_calculator import XPCalculator
from models.lesson import AnswerSubmission

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/generate")
async def generate_review_quiz(current_user: dict = Depends(get_current_user)):
    """
    Generate a dynamic review quiz based on past mistakes
    FR17: Dynamic quiz based on past mistakes
    """
    try:
        with get_db_cursor() as cursor:
            # Get user's active mistakes from user_mistakes table
            cursor.execute(
                """SELECT question_id, source_type, created_at
                   FROM user_mistakes
                   WHERE user_id = %s
                   ORDER BY created_at DESC
                   LIMIT 20""",
                (current_user["user_id"],)
            )
            mistake_records = cursor.fetchall()
            
            # Collect question IDs
            question_ids = [m["question_id"] for m in mistake_records]
            
            # If no mistakes found, try general review
            if not question_ids:
                cursor.execute(
                    "SELECT cefr_level FROM users WHERE id = %s",
                    (current_user["user_id"],)
                )
                user = cursor.fetchone()
                return {
                    "title": "Review Mode",
                    "description": "Great job! You have no pending mistakes to review.",
                    "total_questions": 0,
                    "based_on_mistakes": 0,
                    "questions": [],
                    "xp_reward": 0,
                    "can_exit_early": True,
                    "message": "You're all caught up! Go generate some more mistakes... or not! 🎉"
                }
            
            # Limit to 10 questions for the quiz
            question_ids = question_ids[:10]
            
            # Get actual questions if ids exist
            if question_ids:
                placeholders = ','.join(['%s'] * len(question_ids))
                cursor.execute(
                    f"""SELECT id, type, content, skill_tag, correct_answer
                       FROM questions WHERE id IN ({placeholders})""",
                    tuple(question_ids)
                )
                questions = cursor.fetchall()
            else:
                questions = []
            
            formatted_questions = []
            for q in questions:
                content = q["content"] if isinstance(q["content"], dict) else json.loads(q["content"])
                
                # Parse correct_answer if it's a JSON string
                correct_ans = q["correct_answer"]
                try:
                    correct_ans = json.loads(correct_ans)
                except:
                    pass

                formatted_questions.append({
                    "id": q["id"],
                    "type": q["type"],
                    "skill_tag": q["skill_tag"],
                    "correct_answer": correct_ans,
                    **content
                })
            
            if not formatted_questions:
                # No mistakes found - Return empty state
                return {
                    "title": "Review Mode",
                    "description": "Great job! You have no pending mistakes to review.",
                    "total_questions": 0,
                    "based_on_mistakes": 0,
                    "questions": [],
                    "xp_reward": 0,
                    "can_exit_early": True,
                    "message": "You're all caught up! Go generate some more mistakes... or not! 🎉"
                }
            
            return {
                "title": "Review Mode",
                "description": "Practice questions based on your past mistakes",
                "total_questions": len(formatted_questions),
                "based_on_mistakes": len(mistake_records),
                "questions": formatted_questions,
                "xp_reward": 30,
                "can_exit_early": True
            }
    except Exception as e:
        logger.error(f"Generate review quiz error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate review quiz")


@router.post("/submit")
async def submit_review(
    answers: List[AnswerSubmission],
    partial: bool = False,
    current_user: dict = Depends(get_current_user)
):
    """
    Submit review quiz answers
    Supports partial submission if user exits early
    """
    try:
        with get_db_cursor() as cursor:
            # Get user data
            cursor.execute(
                "SELECT xp_total, current_streak FROM users WHERE id = %s",
                (current_user["user_id"],)
            )
            user = cursor.fetchone()
            
            # Process answers
            correct_count = 0
            results = []
            updated_words = []
            
            for answer in answers:
                cursor.execute(
                    "SELECT correct_answer, skill_tag FROM questions WHERE id = %s",
                    (answer.question_id,)
                )
                question = cursor.fetchone()
                
                if question:
                    correct_answer = question["correct_answer"]
                    if isinstance(correct_answer, str):
                        try:
                            correct_answer = json.loads(correct_answer)
                        except:
                            pass
                    
                    is_correct = str(answer.user_answer).lower().strip() == str(correct_answer).lower().strip()
                    
                    if is_correct:
                        correct_count += 1
                        # Remove from user_mistakes if correct
                        cursor.execute(
                            "DELETE FROM user_mistakes WHERE user_id = %s AND question_id = %s",
                            (current_user["user_id"], answer.question_id)
                        )
                        updated_words.append(answer.question_id)
                    
                    results.append({
                        "question_id": answer.question_id,
                        "is_correct": is_correct,
                        "skill_tag": question["skill_tag"]
                    })
            
            # Calculate XP (reduced for partial completion)
            total_questions = len(answers)
            completion_rate = 1.0 if not partial else 0.7
            
            xp_data = XPCalculator.calculate_lesson_xp(
                correct_count,
                total_questions,
                user["current_streak"] or 0,
                "daily"
            )
            xp_earned = int(xp_data["xp_total"] * completion_rate)
            
            # Update user XP
            cursor.execute(
                "UPDATE users SET xp_total = xp_total + %s WHERE id = %s",
                (xp_earned, current_user["user_id"])
            )
            
            # Save progress
            cursor.execute(
                """INSERT INTO user_progress 
                   (user_id, lesson_id, score, xp_earned, answers, completed_at, time_spent_seconds)
                   VALUES (%s, 0, %s, %s, %s, %s, 0)""",
                (
                    current_user["user_id"],
                    int((correct_count / total_questions) * 100) if total_questions > 0 else 0,
                    xp_earned,
                    json.dumps(results),
                    datetime.now()
                )
            )
            
            # Analyze performance
            analysis = AIAdaptiveEngine.analyze_performance(results)
            
            return {
                "success": True,
                "partial": partial,
                "score": int((correct_count / total_questions) * 100) if total_questions > 0 else 0,
                "correct_count": correct_count,
                "total_questions": total_questions,
                "xp_earned": xp_earned,
                "analysis": analysis,
                "message": "Review completed!" if not partial else "Progress saved. Come back to continue!"
            }
    except Exception as e:
        logger.error(f"Submit review error: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit review")


@router.get("/stats")
async def get_review_stats(current_user: dict = Depends(get_current_user)):
    """Get user's review statistics"""
    try:
        with get_db_cursor() as cursor:
            # Get mistake counts by skill
            cursor.execute(
                """SELECT 
                       COUNT(*) as total_reviews,
                       AVG(score) as avg_score
                   FROM user_progress
                   WHERE user_id = %s AND lesson_id = 0""",
                (current_user["user_id"],)
            )
            stats = cursor.fetchone()
            
            # Get vocabulary stats
            cursor.execute(
                """SELECT 
                       COUNT(*) as total_words,
                       SUM(CASE WHEN mastered = TRUE THEN 1 ELSE 0 END) as mastered_words,
                       SUM(mistake_count) as total_mistakes
                   FROM vocabulary_lists
                   WHERE user_id = %s""",
                (current_user["user_id"],)
            )
            vocab_stats = cursor.fetchone()
            
            return {
                "total_reviews": stats["total_reviews"] or 0,
                "average_score": round(stats["avg_score"] or 0, 1),
                "vocabulary": {
                    "total_words": vocab_stats["total_words"] or 0,
                    "mastered": vocab_stats["mastered_words"] or 0,
                    "total_mistakes": vocab_stats["total_mistakes"] or 0
                },
                "recommendation": "Keep practicing to improve your weak areas!"
            }
    except Exception as e:
        logger.error(f"Get review stats error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get stats")


def _generate_general_review(level: str):
    """Generate general review questions when no mistakes exist"""
    questions = [
        {
            "id": 1, "type": "mcq", "skill_tag": "grammar",
            "question": "She ___ to work every day.",
            "options": ["go", "goes", "going", "gone"]
        },
        {
            "id": 2, "type": "mcq", "skill_tag": "vocabulary",
            "question": "The opposite of 'happy' is:",
            "options": ["joyful", "sad", "excited", "calm"]
        },
        {
            "id": 3, "type": "mcq", "skill_tag": "grammar",
            "question": "I ___ watching TV when you called.",
            "options": ["am", "was", "were", "is"]
        },
        {
            "id": 4, "type": "gap_fill", "skill_tag": "grammar",
            "sentence": "They have lived here ___ 2010.",
            "options": ["for", "since", "during", "while"]
        },
        {
            "id": 5, "type": "mcq", "skill_tag": "vocabulary",
            "question": "A person who teaches is called a:",
            "options": ["doctor", "teacher", "engineer", "lawyer"]
        }
    ]
    
    return {
        "title": "General Review",
        "description": "Practice some general English questions",
        "total_questions": len(questions),
        "based_on_mistakes": 0,
        "questions": questions,
        "xp_reward": 20,
        "can_exit_early": True,
        "message": "Complete more lessons to get personalized review questions!"
    }
