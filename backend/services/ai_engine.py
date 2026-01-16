"""
AI Adaptive Engine - Core Intelligence Service
Handles content adaptation based on student performance
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
import logging

logger = logging.getLogger(__name__)


class AIAdaptiveEngine:
    """
    AI Adaptive Engine responsible for:
    - Analyzing student performance
    - Selecting appropriate content difficulty
    - Generating personalized recommendations
    """
    
    # Difficulty adjustment thresholds
    DIFFICULTY_UP_THRESHOLD = 0.85  # 85% correct -> increase difficulty
    DIFFICULTY_DOWN_THRESHOLD = 0.60  # Below 60% -> decrease difficulty
    
    # Skill weights for overall level calculation
    SKILL_WEIGHTS = {
        "grammar": 0.25,
        "vocabulary": 0.25,
        "pronunciation": 0.20,
        "speaking": 0.15,
        "listening": 0.15
    }
    
    @staticmethod
    def calculate_cefr_level(placement_results: Dict[str, float]) -> str:
        """
        Calculate CEFR level from placement test results
        
        Args:
            placement_results: Dict with skill scores (0-100)
        
        Returns:
            CEFR level string (A1-C2)
        """
        # Calculate weighted average
        total_weight = 0
        weighted_sum = 0
        
        for skill, weight in AIAdaptiveEngine.SKILL_WEIGHTS.items():
            if skill in placement_results:
                weighted_sum += placement_results[skill] * weight
                total_weight += weight
        
        if total_weight == 0:
            return "A1"
        
        avg_score = weighted_sum / total_weight
        
        # Map score to CEFR level
        if avg_score >= 90:
            return "C2"
        elif avg_score >= 80:
            return "C1"
        elif avg_score >= 70:
            return "B2"
        elif avg_score >= 55:
            return "B1"
        elif avg_score >= 40:
            return "A2"
        else:
            return "A1"
    
    @staticmethod
    def analyze_performance(answers: List[Dict]) -> Dict[str, Any]:
        """
        Analyze lesson performance and identify weak areas
        
        Args:
            answers: List of answer results with skill tags
        
        Returns:
            Analysis with skill breakdown and recommendations
        """
        skill_stats = {}
        total_correct = 0
        total_questions = len(answers)
        
        for answer in answers:
            skill = answer.get("skill_tag", "general")
            is_correct = answer.get("is_correct", False)
            
            if skill not in skill_stats:
                skill_stats[skill] = {"correct": 0, "total": 0}
            
            skill_stats[skill]["total"] += 1
            if is_correct:
                skill_stats[skill]["correct"] += 1
                total_correct += 1
        
        # Calculate percentages
        overall_accuracy = (total_correct / total_questions * 100) if total_questions > 0 else 0
        
        skill_breakdown = []
        weak_skills = []
        strong_skills = []
        
        for skill, stats in skill_stats.items():
            accuracy = (stats["correct"] / stats["total"] * 100) if stats["total"] > 0 else 0
            skill_breakdown.append({
                "skill": skill,
                "accuracy": round(accuracy, 1),
                "correct": stats["correct"],
                "total": stats["total"]
            })
            
            if accuracy < 60:
                weak_skills.append(skill)
            elif accuracy >= 85:
                strong_skills.append(skill)
        
        return {
            "overall_accuracy": round(overall_accuracy, 1),
            "total_correct": total_correct,
            "total_questions": total_questions,
            "skill_breakdown": skill_breakdown,
            "weak_skills": weak_skills,
            "strong_skills": strong_skills,
            "needs_review": overall_accuracy < 70
        }
    
    @staticmethod
    def get_difficulty_adjustment(recent_scores: List[float]) -> int:
        """
        Determine difficulty adjustment based on recent performance
        
        Returns:
            -1 (decrease), 0 (maintain), or 1 (increase)
        """
        if len(recent_scores) < 3:
            return 0
        
        # Consider last 5 scores
        recent = recent_scores[-5:]
        avg_score = sum(recent) / len(recent)
        
        if avg_score >= AIAdaptiveEngine.DIFFICULTY_UP_THRESHOLD * 100:
            return 1
        elif avg_score < AIAdaptiveEngine.DIFFICULTY_DOWN_THRESHOLD * 100:
            return -1
        return 0
    
    @staticmethod
    def select_next_content(user_level: str, skill_stats: Dict, 
                           completed_lessons: List[int]) -> Dict[str, Any]:
        """
        Select the next best content for the user
        
        Args:
            user_level: Current CEFR level
            skill_stats: User's skill performance statistics
            completed_lessons: List of completed lesson IDs
        
        Returns:
            Recommendation for next content
        """
        # Find weakest skill
        weakest_skill = None
        lowest_accuracy = 100
        
        for skill, stats in skill_stats.items():
            if stats.get("accuracy", 100) < lowest_accuracy:
                lowest_accuracy = stats["accuracy"]
                weakest_skill = skill
        
        return {
            "recommended_level": user_level,
            "focus_skill": weakest_skill or "vocabulary",
            "suggested_lesson_type": "review" if lowest_accuracy < 60 else "daily",
            "priority_skills": [s for s, stats in skill_stats.items() 
                              if stats.get("accuracy", 100) < 70]
        }
    
    @staticmethod
    def generate_review_questions(mistakes: List[Dict], count: int = 10) -> List[int]:
        """
        Select questions for review based on past mistakes
        
        Args:
            mistakes: List of mistake records with question_ids and timestamps
            count: Number of questions to select
        
        Returns:
            List of question IDs for review
        """
        # Sort by mistake frequency and recency
        mistake_scores = {}
        now = datetime.now()
        
        for mistake in mistakes:
            q_id = mistake.get("question_id")
            mistake_time = mistake.get("timestamp", now)
            
            if isinstance(mistake_time, str):
                mistake_time = datetime.fromisoformat(mistake_time)
            
            # Recent mistakes get higher priority
            days_ago = (now - mistake_time).days
            recency_score = max(0, 30 - days_ago) / 30  # 0-1 based on recency
            
            if q_id not in mistake_scores:
                mistake_scores[q_id] = {"count": 0, "recency": 0}
            
            mistake_scores[q_id]["count"] += 1
            mistake_scores[q_id]["recency"] = max(
                mistake_scores[q_id]["recency"], 
                recency_score
            )
        
        # Calculate final score
        scored_questions = []
        for q_id, scores in mistake_scores.items():
            final_score = scores["count"] * 0.6 + scores["recency"] * 0.4
            scored_questions.append((q_id, final_score))
        
        # Sort by score and return top N
        scored_questions.sort(key=lambda x: x[1], reverse=True)
        return [q[0] for q in scored_questions[:count]]
    
    @staticmethod
    def generate_vocabulary_recommendations(mistakes: List[Dict], 
                                           known_words: List[str]) -> List[Dict]:
        """
        Generate personalized vocabulary list based on mistakes
        
        Args:
            mistakes: Vocabulary-related mistakes
            known_words: Words the user has mastered
        
        Returns:
            List of recommended vocabulary items
        """
        word_stats = {}
        
        for mistake in mistakes:
            word = mistake.get("word", "").lower()
            if word and word not in known_words:
                if word not in word_stats:
                    word_stats[word] = {
                        "word": word,
                        "translation": mistake.get("translation", ""),
                        "mistake_count": 0,
                        "context": mistake.get("context", "")
                    }
                word_stats[word]["mistake_count"] += 1
        
        # Sort by mistake count
        recommendations = list(word_stats.values())
        recommendations.sort(key=lambda x: x["mistake_count"], reverse=True)
        
        return recommendations[:20]  # Return top 20 words to review
