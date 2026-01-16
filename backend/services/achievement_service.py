"""
Achievement Service
Handles logic for unlocking and awarding achievements
"""
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class AchievementService:
    @staticmethod
    def check_achievements(cursor, user_id, current_stats, new_activity):
        """
        Check and award achievements based on user stats and recent activity.
        
        Args:
            cursor: Database cursor
            user_id: User ID
            current_stats: Dict containing user stats (xp_total, current_streak, etc.)
            new_activity: Dict containing details of the new activity (e.g., lesson completed)
            
        Returns:
            List of newly awarded achievements
        """
        new_awards = []
        
        # Define all available achievements and their conditions
        # Lambda functions return True if condition is met
        achievements = {
            "first_lesson": {
                "check": lambda s, a: s.get("total_lessons", 0) >= 1,
                "type": "lesson"
            },
            "xp_100": {
                "check": lambda s, a: s.get("xp_total", 0) >= 100,
                "type": "xp"
            },
            "xp_500": {
                "check": lambda s, a: s.get("xp_total", 0) >= 500,
                "type": "xp"
            },
            "xp_1000": {
                "check": lambda s, a: s.get("xp_total", 0) >= 1000,
                "type": "xp"
            },
            "streak_3": {
                "check": lambda s, a: s.get("current_streak", 0) >= 3,
                "type": "streak"
            },
            "streak_7": {
                "check": lambda s, a: s.get("current_streak", 0) >= 7,
                "type": "streak"
            },
            "streak_30": {
                "check": lambda s, a: s.get("current_streak", 0) >= 30,
                "type": "streak"
            },
            "perfect_lesson": {
                "check": lambda s, a: a.get("score", 0) == 100,
                "type": "performance"
            },
            "first_speaking": {
                "check": lambda s, a: a.get("type") == "speaking",
                "type": "lesson"
            }
        }
        
        # Get existing achievements to avoid duplicates
        cursor.execute(
            "SELECT badge_type FROM achievements WHERE user_id = %s",
            (user_id,)
        )
        existing_badges = {row["badge_type"] for row in cursor.fetchall()}
        
        # Check each achievement
        for badge_type, criteria in achievements.items():
            if badge_type not in existing_badges:
                if criteria["check"](current_stats, new_activity):
                    # Award key achievement
                    logger.info(f"Awarding achievement {badge_type} to user {user_id}")
                    cursor.execute(
                        """INSERT INTO achievements (user_id, badge_type, earned_at)
                           VALUES (%s, %s, %s)""",
                        (user_id, badge_type, datetime.now())
                    )
                    new_awards.append(badge_type)
        
        return new_awards
