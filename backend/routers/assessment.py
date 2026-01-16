"""
Assessment Router - UC2, UC3: Placement Test and Level Assignment
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from datetime import datetime
import json
import logging

from utils.jwt_handler import get_current_user
from database import get_db_cursor
from services.ai_engine import AIAdaptiveEngine
from models.lesson import LessonResult, AnswerSubmission

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/placement")
async def get_placement_test(current_user: dict = Depends(get_current_user)):
    """
    Get placement test questions
    FR2: Present Placement Test to determine initial CEFR level
    """
    try:
        with get_db_cursor() as cursor:
            # Check if user already has a level
            cursor.execute(
                "SELECT cefr_level FROM users WHERE id = %s",
                (current_user["user_id"],)
            )
            user = cursor.fetchone()
            
            # Get placement test lesson
            cursor.execute(
                """SELECT id FROM lessons WHERE type = 'placement' LIMIT 1"""
            )
            lesson = cursor.fetchone()
            
            if not lesson:
                raise HTTPException(status_code=404, detail="Placement test not found")
            
            # Fetch 3 random questions for each difficulty level (1-5)
            # This ensures we get exactly 15 questions distributed across all levels
            all_questions = []
            for difficulty in range(1, 6):
                cursor.execute(
                    """SELECT id, type, content, skill_tag, difficulty, correct_answer
                       FROM questions 
                       WHERE lesson_id = %s AND difficulty = %s
                       ORDER BY RAND()
                       LIMIT 3""",
                    (lesson["id"], difficulty)
                )
                level_questions = cursor.fetchall()
                all_questions.extend(level_questions)
            
            # Format questions for frontend
            formatted_questions = []
            for q in all_questions:
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
                    "difficulty": q["difficulty"],
                    "correct_answer": correct_ans,
                    **content
                })
            
            return {
                "lesson_id": lesson["id"],
                "title": "Placement Test",
                "description": "Complete this test to determine your English level",
                "time_limit_minutes": 30,
                "already_completed": user["cefr_level"] is not None,
                "current_level": user["cefr_level"],
                "questions": formatted_questions
            }
    except Exception as e:
        logger.error(f"Get placement test error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load placement test")


@router.post("/submit")
async def submit_placement_test(
    answers: List[AnswerSubmission],
    current_user: dict = Depends(get_current_user)
):
    """
    Submit placement test and get CEFR level assignment
    FR3: Assign CEFR level based on total correct answers (out of 15)
    Scale:
    0-3: A1
    4-6: A2
    7-10: B1
    11-13: B2
    14-15: C1
    """
    try:
        with get_db_cursor() as cursor:
            total_correct = 0
            results = []
            
            # Calculate score
            for answer in answers:
                cursor.execute(
                    """SELECT correct_answer, skill_tag, difficulty
                       FROM questions WHERE id = %s""",
                    (answer.question_id,)
                )
                question = cursor.fetchone()
                
                if question:
                    correct_answer = question["correct_answer"]
                    try:
                        # Attempt to decode JSON if it looks like a JSON string
                        # This strips the extra quotes added for DB constraint
                        correct_answer = json.loads(correct_answer)
                    except:
                        pass
                    
                    # Normalize answer comparison
                    user_ans = str(answer.user_answer).lower().strip()
                    correct_ans = str(correct_answer).lower().strip()
                    
                    is_correct = user_ans == correct_ans
                    if is_correct:
                        total_correct += 1
                    
                    results.append({
                        "question_id": answer.question_id,
                        "is_correct": is_correct,
                        "skill_tag": question["skill_tag"]
                    })
            
            # Determine CEFR level based on score
            if total_correct <= 3:
                cefr_level = "A1"
            elif total_correct <= 6:
                cefr_level = "A2"
            elif total_correct <= 10:
                cefr_level = "B1"
            elif total_correct <= 13:
                cefr_level = "B2"
            else:
                cefr_level = "C1"
            
            # Update user's level
            cursor.execute(
                """UPDATE users SET cefr_level = %s WHERE id = %s""",
                (cefr_level, current_user["user_id"])
            )
            
            # Store assessment results
            cursor.execute(
                """INSERT INTO user_progress 
                   (user_id, lesson_id, score, xp_earned, answers, completed_at, time_spent_seconds)
                   VALUES (%s, 0, %s, 0, %s, %s, 0)""",
                (
                    current_user["user_id"],
                    int((total_correct / len(answers)) * 100) if answers else 0,
                    json.dumps(results),
                    datetime.now()
                )
            )

            # Save mistakes for review
            for res in results:
                if not res["is_correct"]:
                    cursor.execute(
                        """INSERT INTO user_mistakes (user_id, question_id, source_type)
                           VALUES (%s, %s, 'placement')
                           ON DUPLICATE KEY UPDATE created_at = NOW()""",
                        (current_user["user_id"], res["question_id"])
                    )
            
            # Calculate skill breakdown
            skill_stats = {}
            for res in results:
                skill = res.get("skill_tag") or "general"
                if skill not in skill_stats:
                    skill_stats[skill] = {"correct": 0, "total": 0}
                skill_stats[skill]["total"] += 1
                if res["is_correct"]:
                    skill_stats[skill]["correct"] += 1
            
            skill_breakdown = []
            for skill, stats in skill_stats.items():
                score_pct = round((stats["correct"] / stats["total"]) * 100) if stats["total"] > 0 else 0
                skill_breakdown.append({
                    "skill": skill,
                    "score": score_pct,
                    "correct": stats["correct"],
                    "total": stats["total"]
                })

            return {
                "success": True,
                "assigned_level": cefr_level,
                "total_questions": len(answers),
                "correct_answers": total_correct,
                "score_percentage": round((total_correct / len(answers)) * 100, 1) if answers else 0,
                "skill_breakdown": skill_breakdown,
                "message": f"Congratulations! You've been placed at {cefr_level} level."
            }
    except Exception as e:
        logger.error(f"Submit placement test error: {e}")
        # Return specific error for debugging
        raise HTTPException(status_code=500, detail=f"Failed to process placement test: {str(e)}")


@router.get("/transition/{target_level}")
async def get_transition_test(
    target_level: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get transition test for level advancement
    """
    valid_levels = ["A1", "A2", "B1", "B2", "C1", "C2"]
    if target_level.upper() not in valid_levels:
        raise HTTPException(status_code=400, detail="Invalid target level")
    
    try:
        with get_db_cursor() as cursor:
            # Get user's current level
            cursor.execute(
                "SELECT cefr_level FROM users WHERE id = %s",
                (current_user["user_id"],)
            )
            user = cursor.fetchone()
            
            current_index = valid_levels.index(user["cefr_level"]) if user["cefr_level"] else 0
            target_index = valid_levels.index(target_level.upper())
            
            if target_index <= current_index:
                raise HTTPException(
                    status_code=400,
                    detail="Target level must be higher than current level"
                )
            
            # Get transition test questions for target level
            cursor.execute(
                """SELECT id FROM lessons 
                   WHERE type = 'transition' AND cefr_level = %s
                   LIMIT 1""",
                (target_level.upper(),)
            )
            lesson = cursor.fetchone()
            
            if not lesson:
                return {
                    "lesson_id": 0,
                    "title": f"Transition Test to {target_level.upper()}",
                    "questions": _get_sample_transition_questions(target_level.upper())
                }
            
            cursor.execute(
                """SELECT id, type, content, skill_tag
                   FROM questions WHERE lesson_id = %s""",
                (lesson["id"],)
            )
            questions = cursor.fetchall()
            
            return {
                "lesson_id": lesson["id"],
                "title": f"Transition Test to {target_level.upper()}",
                "current_level": user["cefr_level"],
                "target_level": target_level.upper(),
                "questions": [
                    {
                        "id": q["id"],
                        "type": q["type"],
                        "skill_tag": q["skill_tag"],
                        **(q["content"] if isinstance(q["content"], dict) else json.loads(q["content"]))
                    }
                    for q in questions
                ]
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get transition test error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load transition test")


def _get_sample_placement_questions() -> List[Dict[str, Any]]:
    """Return sample placement test questions"""
    return [
        {
            "id": "sample_1",
            "type": "mcq",
            "skill_tag": "grammar",
            "difficulty": 1,
            "question": "She ___ to school every day.",
            "options": ["go", "goes", "going", "gone"],
            "correct_answer": "goes"
        },
        {
            "id": "sample_2",
            "type": "mcq",
            "skill_tag": "vocabulary",
            "difficulty": 1,
            "question": "The opposite of 'hot' is:",
            "options": ["warm", "cold", "cool", "heat"],
            "correct_answer": "cold"
        },
        {
            "id": "sample_3",
            "type": "mcq",
            "skill_tag": "grammar",
            "difficulty": 2,
            "question": "I ___ dinner when the phone rang.",
            "options": ["cook", "cooked", "was cooking", "have cooked"],
            "correct_answer": "was cooking"
        },
        {
            "id": "sample_4",
            "type": "mcq",
            "skill_tag": "vocabulary",
            "difficulty": 2,
            "question": "Choose the synonym of 'happy':",
            "options": ["sad", "joyful", "angry", "tired"],
            "correct_answer": "joyful"
        },
        {
            "id": "sample_5",
            "type": "mcq",
            "skill_tag": "grammar",
            "difficulty": 3,
            "question": "If I ___ known, I would have helped.",
            "options": ["have", "had", "has", "having"],
            "correct_answer": "had"
        },
        {
            "id": "sample_6",
            "type": "gap_fill",
            "skill_tag": "grammar",
            "difficulty": 2,
            "sentence": "They have been living here ___ five years.",
            "options": ["for", "since", "during", "while"],
            "correct_answer": "for"
        },
        {
            "id": "sample_7",
            "type": "mcq",
            "skill_tag": "vocabulary",
            "difficulty": 3,
            "question": "The word 'ubiquitous' means:",
            "options": ["rare", "everywhere", "unique", "ancient"],
            "correct_answer": "everywhere"
        },
        {
            "id": "sample_8",
            "type": "mcq",
            "skill_tag": "grammar",
            "difficulty": 4,
            "question": "Not until I arrived ___ the news.",
            "options": ["I heard", "did I hear", "I did hear", "heard I"],
            "correct_answer": "did I hear"
        },
        {
            "id": "sample_9",
            "type": "mcq",
            "skill_tag": "reading",
            "difficulty": 3,
            "question": "In formal writing, which is correct?",
            "options": ["gonna", "going to", "gon'", "gunna"],
            "correct_answer": "going to"
        },
        {
            "id": "sample_10",
            "type": "mcq",
            "skill_tag": "grammar",
            "difficulty": 5,
            "question": "The subjunctive mood is used in:",
            "options": [
                "I wish he was here",
                "I wish he were here",
                "I wish he is here",
                "I wish he be here"
            ],
            "correct_answer": "I wish he were here"
        }
    ]


def _get_sample_transition_questions(level: str) -> List[Dict[str, Any]]:
    """Return sample transition test questions for a specific level"""
    # Return questions appropriate for the target level
    base_questions = _get_sample_placement_questions()
    level_index = ["A1", "A2", "B1", "B2", "C1", "C2"].index(level)
    min_difficulty = max(1, level_index)
    return [q for q in base_questions if q.get("difficulty", 1) >= min_difficulty]
