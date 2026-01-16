"""
XP and Level Calculator Service
"""
from config import settings
from typing import Dict, Tuple


class XPCalculator:
    """Calculate XP rewards and level progression"""
    
    # XP thresholds for each CEFR level (cumulative totals)
    # A1 -> A2: Need 5000 XP
    # A2 -> B1: Need 10000 XP
    # B1 -> B2: Need 15000 XP
    # B2 -> C1: Need 20000 XP
    # C1 -> C2: Need 25000 XP
    LEVEL_THRESHOLDS = {
        "A1": 0,
        "A2": 5000,
        "B1": 10000,
        "B2": 15000,
        "C1": 20000,
        "C2": 25000
    }
    
    @staticmethod
    def calculate_lesson_xp(correct_answers: int, total_questions: int, 
                           current_streak: int, lesson_type: str) -> Dict:
        """
        Calculate XP earned for a lesson
        
        Returns:
            Dict with xp_base, xp_streak_bonus, xp_total
        """
        # Base XP from correct answers
        xp_base = correct_answers * settings.XP_PER_CORRECT_ANSWER
        
        # Completion bonus based on lesson type
        completion_bonus = 0
        if correct_answers >= total_questions * 0.6:  # At least 60% correct
            if lesson_type == "daily":
                completion_bonus = settings.XP_DAILY_LESSON_COMPLETE
            elif lesson_type == "grammar_sprint":
                completion_bonus = settings.XP_GRAMMAR_SPRINT_COMPLETE
            elif lesson_type == "word_sprint":
                completion_bonus = settings.XP_WORD_SPRINT_COMPLETE
        
        # Streak bonus (5 XP per day in streak, max 50)
        streak_bonus = min(current_streak * settings.XP_BONUS_STREAK, 50)
        
        # Perfect score bonus
        perfect_bonus = 25 if correct_answers == total_questions else 0
        
        xp_total = xp_base + completion_bonus + streak_bonus + perfect_bonus
        
        return {
            "xp_base": xp_base,
            "xp_completion_bonus": completion_bonus,
            "xp_streak_bonus": streak_bonus,
            "xp_perfect_bonus": perfect_bonus,
            "xp_total": xp_total
        }
    
    @staticmethod
    def calculate_speaking_xp(fluency_score: float, grammar_score: float, 
                             vocab_score: float, duration_seconds: int) -> int:
        """Calculate XP for speaking sessions"""
        # Average score (0-100)
        avg_score = (fluency_score + grammar_score + vocab_score) / 3
        
        # Base XP based on performance
        base_xp = int(avg_score * 0.4)  # Max 40 XP from score
        
        # Duration bonus (1 XP per 30 seconds, max 20)
        duration_bonus = min(duration_seconds // 30, 20)
        
        return base_xp + duration_bonus + settings.XP_SPEAKING_SESSION
    
    @staticmethod
    def get_level_from_xp(total_xp: int) -> str:
        """Determine CEFR level based on total XP"""
        level = "A1"
        for cefr, threshold in XPCalculator.LEVEL_THRESHOLDS.items():
            if total_xp >= threshold:
                level = cefr
        return level
    
    @staticmethod
    def check_level_up(old_xp: int, new_xp: int) -> Tuple[bool, str, str]:
        """
        Check if user leveled up
        
        Returns:
            Tuple of (level_up: bool, old_level: str, new_level: str)
        """
        old_level = XPCalculator.get_level_from_xp(old_xp)
        new_level = XPCalculator.get_level_from_xp(new_xp)
        
        level_up = new_level != old_level
        return level_up, old_level, new_level
    
    @staticmethod
    def get_xp_to_next_level(current_xp: int) -> Dict:
        """Get XP progress to next level"""
        current_level = XPCalculator.get_level_from_xp(current_xp)
        levels = list(XPCalculator.LEVEL_THRESHOLDS.keys())
        current_index = levels.index(current_level)
        
        if current_index >= len(levels) - 1:
            # Already at max level
            return {
                "current_level": current_level,
                "next_level": None,
                "xp_current": current_xp,
                "xp_needed": 0,
                "xp_for_next": 0,
                "progress_percent": 100
            }
        
        next_level = levels[current_index + 1]
        current_threshold = XPCalculator.LEVEL_THRESHOLDS[current_level]
        next_threshold = XPCalculator.LEVEL_THRESHOLDS[next_level]
        
        xp_in_level = current_xp - current_threshold
        xp_for_level = next_threshold - current_threshold
        progress = int((xp_in_level / xp_for_level) * 100)
        
        return {
            "current_level": current_level,
            "next_level": next_level,
            "xp_current": current_xp,
            "xp_needed": next_threshold - current_xp,
            "xp_for_next": xp_for_level,
            "progress_percent": progress
        }
    
    @staticmethod
    def update_streak(last_activity_date, current_date) -> Tuple[int, bool]:
        """
        Update streak based on activity dates
        
        Returns:
            Tuple of (new_streak_value, streak_maintained)
        """
        if last_activity_date is None:
            return 1, True
        
        days_diff = (current_date - last_activity_date).days
        
        if days_diff == 0:
            # Same day, streak unchanged
            return -1, True  # -1 indicates no change
        elif days_diff == 1:
            # Consecutive day, increment streak
            return 1, True  # Return increment value
        else:
            # Streak broken
            return 1, False  # Reset to 1, streak was broken
