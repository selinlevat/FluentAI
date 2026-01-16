"""
Progress and Achievement Models
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum


class AchievementType(str, Enum):
    STREAK_3 = "streak_3"
    STREAK_7 = "streak_7"
    STREAK_30 = "streak_30"
    STREAK_100 = "streak_100"
    XP_100 = "xp_100"
    XP_500 = "xp_500"
    XP_1000 = "xp_1000"
    XP_5000 = "xp_5000"
    LEVEL_A2 = "level_a2"
    LEVEL_B1 = "level_b1"
    LEVEL_B2 = "level_b2"
    LEVEL_C1 = "level_c1"
    FIRST_LESSON = "first_lesson"
    FIRST_SPEAKING = "first_speaking"
    PERFECT_LESSON = "perfect_lesson"
    GRAMMAR_MASTER = "grammar_master"
    VOCAB_MASTER = "vocab_master"
    CONVERSATION_STARTER = "conversation_starter"


class UserProgress(BaseModel):
    id: int
    user_id: int
    lesson_id: int
    score: int
    xp_earned: int
    answers: Dict[str, Any]
    completed_at: datetime
    time_spent_seconds: int
    
    class Config:
        from_attributes = True


class Achievement(BaseModel):
    id: int
    user_id: int
    badge_type: AchievementType
    earned_at: datetime
    
    class Config:
        from_attributes = True


class AchievementDisplay(BaseModel):
    type: str
    name: str
    description: str
    icon: str
    earned: bool
    earned_at: Optional[datetime] = None


class SkillProgress(BaseModel):
    skill: str
    level: int  # 0-100
    total_questions: int
    correct_answers: int


class DailyGoal(BaseModel):
    target_xp: int
    earned_xp: int
    lessons_completed: int
    target_lessons: int
    time_spent_minutes: int
    target_minutes: int
    completed: bool


class WeeklyProgress(BaseModel):
    day: str
    date: str
    xp_earned: int
    lessons_completed: int
    active: bool


class DashboardData(BaseModel):
    user_id: int
    name: str
    cefr_level: str
    xp_total: int
    current_streak: int
    longest_streak: int
    daily_goal: DailyGoal
    weekly_progress: List[WeeklyProgress]
    skill_breakdown: List[SkillProgress]
    recent_achievements: List[AchievementDisplay]
    next_lesson: Optional[Dict[str, Any]] = None
    vocabulary_to_review: int = 0


class ProgressReport(BaseModel):
    user_id: int
    user_name: str
    generated_at: datetime
    period_start: date
    period_end: date
    cefr_level: str
    xp_earned: int
    lessons_completed: int
    speaking_sessions: int
    average_score: float
    skill_breakdown: List[SkillProgress]
    achievements_earned: List[str]
    streak_data: Dict[str, int]
    improvement_areas: List[str]
    strengths: List[str]


class StudyPlan(BaseModel):
    user_id: int
    daily_goal_minutes: int
    study_days: List[str]
    focus_skills: List[str]
    reminder_time: Optional[str] = None
    notifications_enabled: bool = True
