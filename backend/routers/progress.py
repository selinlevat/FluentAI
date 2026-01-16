"""
Progress Router - UC14, UC15: Dashboard and Reports
"""
from fastapi import APIRouter, HTTPException, Depends, Response
from datetime import datetime, date, timedelta
import json
import logging
from io import BytesIO

from utils.jwt_handler import get_current_user
from database import get_db_cursor
from services.xp_calculator import XPCalculator

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/dashboard")
async def get_dashboard(current_user: dict = Depends(get_current_user)):
    """
    Get user's progress dashboard
    FR19: Display skill progress dashboard
    FR26: Show weekly progress bar
    """
    logger.info(f"Loading dashboard for user {current_user['user_id']}")
    try:
        with get_db_cursor() as cursor:
            # Get user data
            cursor.execute(
                """SELECT name, cefr_level, xp_total, current_streak, longest_streak
                   FROM users WHERE id = %s""",
                (current_user["user_id"],)
            )
            user = cursor.fetchone()
            
            # Get today's progress
            cursor.execute(
                """SELECT COALESCE(SUM(xp_earned), 0) as today_xp,
                          COUNT(*) as lessons_today
                   FROM user_progress
                   WHERE user_id = %s AND DATE(completed_at) = %s""",
                (current_user["user_id"], date.today())
            )
            today = cursor.fetchone()
            
            # Get weekly progress
            weekly_progress = []
            for i in range(7):
                day_date = date.today() - timedelta(days=6-i)
                cursor.execute(
                    """SELECT COALESCE(SUM(xp_earned), 0) as xp,
                              COUNT(*) as lessons
                       FROM user_progress
                       WHERE user_id = %s AND DATE(completed_at) = %s""",
                    (current_user["user_id"], day_date)
                )
                day_data = cursor.fetchone()
                weekly_progress.append({
                    "day": day_date.strftime("%a"),
                    "date": day_date.isoformat(),
                    "xp_earned": day_data["xp"] or 0,
                    "lessons_completed": day_data["lessons"] or 0,
                    "active": (day_data["xp"] or 0) > 0
                })
            
            # Get skill breakdown from user_progress answers (MariaDB compatible)
            cursor.execute(
                """SELECT answers FROM user_progress WHERE user_id = %s""",
                (current_user["user_id"],)
            )
            progress_rows = cursor.fetchall()
            
            # Process answers to calculate skill breakdown
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
            
            skill_breakdown = []
            for skill, stats in skill_stats.items():
                if stats["total"] > 0:
                    accuracy = (stats["correct"] / stats["total"]) * 100
                    skill_breakdown.append({
                        "skill": skill,
                        "level": int(accuracy),
                        "total_questions": stats["total"],
                        "correct_answers": stats["correct"]
                    })
            
            # Default skills if none found
            if not skill_breakdown:
                skill_breakdown = [
                    {"skill": "grammar", "level": 0, "total_questions": 0, "correct_answers": 0},
                    {"skill": "vocabulary", "level": 0, "total_questions": 0, "correct_answers": 0},
                    {"skill": "listening", "level": 0, "total_questions": 0, "correct_answers": 0},
                    {"skill": "speaking", "level": 0, "total_questions": 0, "correct_answers": 0}
                ]
            
            # Get recent achievements
            cursor.execute(
                """SELECT badge_type, earned_at
                   FROM achievements
                   WHERE user_id = %s
                   ORDER BY earned_at DESC LIMIT 5""",
                (current_user["user_id"],)
            )
            achievements = cursor.fetchall()
            
            # Get vocabulary to review count
            cursor.execute(
                """SELECT COUNT(*) as count FROM vocabulary_lists
                   WHERE user_id = %s AND mastered = FALSE""",
                (current_user["user_id"],)
            )
            vocab_count = cursor.fetchone()
            
            # Get total lessons completed (all time)
            cursor.execute(
                """SELECT COUNT(*) as total_lessons
                   FROM user_progress WHERE user_id = %s""",
                (current_user["user_id"],)
            )
            total_lessons = cursor.fetchone()
            
            # XP progress to next level
            xp_progress = XPCalculator.get_xp_to_next_level(user["xp_total"] or 0)
            
            return {
                "user_id": current_user["user_id"],
                "name": user["name"],
                "cefr_level": user["cefr_level"] or "Not set",
                "xp_total": user["xp_total"] or 0,
                "current_streak": user["current_streak"] or 0,
                "longest_streak": user["longest_streak"] or 0,
                "total_lessons_completed": total_lessons["total_lessons"] or 0,
                "xp_progress": xp_progress,
                "daily_goal": {
                    "target_xp": 50,
                    "earned_xp": today["today_xp"] or 0,
                    "lessons_completed": today["lessons_today"] or 0,
                    "target_lessons": 1,
                    "time_spent_minutes": 0,
                    "target_minutes": 15,
                    "completed": (today["today_xp"] or 0) >= 50
                },
                "weekly_progress": weekly_progress,
                "skill_breakdown": skill_breakdown,
                "recent_achievements": [
                    _format_achievement(a["badge_type"], a["earned_at"])
                    for a in achievements
                ],
                "vocabulary_to_review": vocab_count["count"] or 0
            }
    except Exception as e:
        logger.error(f"Get dashboard error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load dashboard")


@router.get("/report/pdf")
async def generate_progress_report(current_user: dict = Depends(get_current_user)):
    """
    Generate PDF progress report
    FR20: Generate downloadable progress report
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        
        with get_db_cursor() as cursor:
            cursor.execute(
                """SELECT name, email, cefr_level, xp_total, current_streak, created_at
                   FROM users WHERE id = %s""",
                (current_user["user_id"],)
            )
            user = cursor.fetchone()
            
            # Get stats
            cursor.execute(
                """SELECT COUNT(*) as total_lessons,
                          COALESCE(AVG(score), 0) as avg_score,
                          COALESCE(SUM(xp_earned), 0) as total_xp
                   FROM user_progress WHERE user_id = %s""",
                (current_user["user_id"],)
            )
            stats = cursor.fetchone()
        
        # Generate PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []
        
        # Title
        elements.append(Paragraph("FluentAI Progress Report", styles['Title']))
        elements.append(Spacer(1, 20))
        
        # User info
        elements.append(Paragraph(f"Student: {user['name']}", styles['Heading2']))
        elements.append(Paragraph(f"Email: {user['email']}", styles['Normal']))
        elements.append(Paragraph(f"Current Level: {user['cefr_level'] or 'Not assessed'}", styles['Normal']))
        elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
        elements.append(Spacer(1, 20))
        
        # Stats table
        data = [
            ['Metric', 'Value'],
            ['Total XP', str(user['xp_total'] or 0)],
            ['Current Streak', f"{user['current_streak'] or 0} days"],
            ['Lessons Completed', str(stats['total_lessons'] or 0)],
            ['Average Score', f"{stats['avg_score']:.1f}%"],
        ]
        
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(table)
        
        doc.build(elements)
        buffer.seek(0)
        
        return Response(
            content=buffer.getvalue(),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=lingualearn_report_{date.today()}.pdf"
            }
        )
    except ImportError:
        raise HTTPException(status_code=500, detail="PDF generation not available")
    except Exception as e:
        logger.error(f"Generate report error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate report")


@router.get("/achievements")
async def get_achievements(current_user: dict = Depends(get_current_user)):
    """Get all achievements with earned status"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                "SELECT badge_type, earned_at FROM achievements WHERE user_id = %s",
                (current_user["user_id"],)
            )
            earned = {a["badge_type"]: a["earned_at"] for a in cursor.fetchall()}
        
        all_achievements = [
            {"type": "streak_3", "name": "3 Day Streak", "description": "Study for 3 days in a row", "icon": "🔥"},
            {"type": "streak_7", "name": "Week Warrior", "description": "Study for 7 days in a row", "icon": "⚡"},
            {"type": "streak_30", "name": "Monthly Master", "description": "Study for 30 days in a row", "icon": "🏆"},
            {"type": "xp_100", "name": "First Steps", "description": "Earn 100 XP", "icon": "👣"},
            {"type": "xp_500", "name": "Rising Star", "description": "Earn 500 XP", "icon": "⭐"},
            {"type": "xp_1000", "name": "XP Champion", "description": "Earn 1000 XP", "icon": "🌟"},
            {"type": "first_lesson", "name": "Getting Started", "description": "Complete your first lesson", "icon": "📖"},
            {"type": "first_speaking", "name": "Finding Voice", "description": "Complete first speaking session", "icon": "🎤"},
            {"type": "perfect_lesson", "name": "Perfectionist", "description": "Get 100% on a lesson", "icon": "💯"},
            {"type": "level_a2", "name": "A2 Achieved", "description": "Reach A2 level", "icon": "📈"},
            {"type": "level_b1", "name": "B1 Achieved", "description": "Reach B1 level", "icon": "📊"},
            {"type": "level_b2", "name": "B2 Achieved", "description": "Reach B2 level", "icon": "🎯"},
        ]
        
        return {
            "achievements": [
                {
                    **a,
                    "earned": a["type"] in earned,
                    "earned_at": earned.get(a["type"]).isoformat() if a["type"] in earned else None
                }
                for a in all_achievements
            ],
            "total_earned": len(earned),
            "total_available": len(all_achievements)
        }
    except Exception as e:
        logger.error(f"Get achievements error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load achievements")


@router.get("/skill-badges")
async def get_skill_badges(current_user: dict = Depends(get_current_user)):
    """
    Get user's skill progress badges
    Returns daily XP progress, grammar sprint, word sprint percentages
    """
    user_id = current_user["user_id"]
    
    try:
        with get_db_cursor() as cursor:
            # Günlük XP hesapla (bugünkü XP / hedef XP * 100)
            cursor.execute("""
                SELECT COALESCE(SUM(xp_earned), 0) as daily_xp 
                FROM user_progress 
                WHERE user_id = %s AND DATE(completed_at) = %s
            """, (user_id, date.today()))
            daily_xp = cursor.fetchone()["daily_xp"] or 0
            daily_xp_percent = min((daily_xp / 50) * 100, 100)
            
            # Grammar Sprint ilerlemesi (tamamlanan/toplam * 100)
            # Hedef: 20 grammar sprint testi
            cursor.execute("""
                SELECT COUNT(*) as completed 
                FROM user_progress up
                JOIN lessons l ON up.lesson_id = l.id
                WHERE up.user_id = %s AND l.type = 'grammar_sprint'
            """, (user_id,))
            grammar_completed = cursor.fetchone()["completed"] or 0
            grammar_percent = min((grammar_completed / 20) * 100, 100)
            
            # Word Sprint ilerlemesi
            # Hedef: 20 word sprint testi
            cursor.execute("""
                SELECT COUNT(*) as completed 
                FROM user_progress up
                JOIN lessons l ON up.lesson_id = l.id
                WHERE up.user_id = %s AND l.type = 'word_sprint'
            """, (user_id,))
            word_completed = cursor.fetchone()["completed"] or 0
            word_percent = min((word_completed / 20) * 100, 100)
            
            return {
                "daily_xp": round(daily_xp_percent),
                "grammar_sprint": round(grammar_percent),
                "word_sprint": round(word_percent),
                "details": {
                    "daily_xp_earned": int(daily_xp),
                    "daily_xp_target": 50,
                    "grammar_tests_completed": int(grammar_completed),
                    "grammar_tests_target": 20,
                    "word_tests_completed": int(word_completed),
                    "word_tests_target": 20
                }
            }
    except Exception as e:
        logger.error(f"Error fetching badges: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch skill badges")


def _format_achievement(badge_type: str, earned_at) -> dict:
    """Format achievement for display"""
    achievement_info = {
        "streak_3": {"name": "3 Day Streak", "icon": "🔥"},
        "streak_7": {"name": "Week Warrior", "icon": "⚡"},
        "streak_30": {"name": "Monthly Master", "icon": "🏆"},
        "xp_100": {"name": "First Steps", "icon": "👣"},
        "xp_500": {"name": "Rising Star", "icon": "⭐"},
        "first_lesson": {"name": "Getting Started", "icon": "📖"},
        "perfect_lesson": {"name": "Perfectionist", "icon": "💯"},
    }
    
    info = achievement_info.get(badge_type, {"name": badge_type, "icon": "🏅"})
    return {
        "type": badge_type,
        "name": info["name"],
        "icon": info["icon"],
        "earned": True,
        "earned_at": earned_at.isoformat() if earned_at else None
    }
