"""
Lesson and Question Models
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from datetime import datetime
from enum import Enum


class QuestionType(str, Enum):
    MCQ = "mcq"                      # Multiple choice
    GAP_FILL = "gap_fill"            # Fill in the blank
    MATCHING = "matching"            # Match pairs
    PICTURE_TO_WORD = "picture_word" # Image-based question
    WORD_TO_PICTURE = "word_picture" # Word to image
    TRANSLATION = "translation"      # Translate sentence
    LISTENING = "listening"          # Listen and answer
    REORDER = "reorder"              # Reorder words/sentences
    TRUE_FALSE = "true_false"        # True or false


class SkillTag(str, Enum):
    GRAMMAR = "grammar"
    VOCABULARY = "vocabulary"
    PRONUNCIATION = "pronunciation"
    SPEAKING = "speaking"
    LISTENING = "listening"
    READING = "reading"


class LessonType(str, Enum):
    DAILY = "daily"
    GRAMMAR_SPRINT = "grammar_sprint"
    WORD_SPRINT = "word_sprint"
    PLACEMENT = "placement"
    TRANSITION = "transition"
    REVIEW = "review"


class Question(BaseModel):
    id: int
    lesson_id: int
    type: QuestionType
    content: Dict[str, Any]  # JSON content with question details
    correct_answer: Any
    skill_tag: SkillTag
    difficulty: int = Field(ge=1, le=5, default=1)
    xp_value: int = 10
    
    class Config:
        from_attributes = True


class QuestionCreate(BaseModel):
    lesson_id: int
    type: QuestionType
    content: Dict[str, Any]
    correct_answer: Any
    skill_tag: SkillTag
    difficulty: int = 1
    xp_value: int = 10


class Lesson(BaseModel):
    id: int
    pack_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    type: LessonType
    cefr_level: str
    xp_reward: int = 50
    order_index: int = 0
    is_locked: bool = False
    questions_count: int = 10
    
    class Config:
        from_attributes = True


class LessonPack(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    cefr_level: str
    order_index: int
    is_locked: bool = False
    lessons_count: int = 0
    completed_count: int = 0
    icon: Optional[str] = None
    
    class Config:
        from_attributes = True


class LessonWithQuestions(Lesson):
    questions: List[Question] = []


class AnswerSubmission(BaseModel):
    question_id: Any  # Can be int (from DB) or string (sample questions like "sample_1")
    user_answer: Any
    time_taken_ms: Optional[int] = None
    question_text: Optional[str] = None      # For sample questions - the question text
    correct_answer: Optional[Any] = None     # For sample questions - the correct answer
    options: Optional[List[str]] = None      # For sample questions - answer options


class LessonSubmission(BaseModel):
    lesson_id: int
    answers: List[AnswerSubmission]
    total_time_seconds: int


class LessonResult(BaseModel):
    lesson_id: int
    score: int
    total_questions: int
    correct_count: int
    xp_earned: int
    streak_bonus: int = 0
    new_streak: int
    level_up: bool = False
    new_level: Optional[str] = None
    mistakes: List[Dict[str, Any]] = []
    new_achievements: List[str] = []
