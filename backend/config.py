"""
FluentAI Configuration Settings
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "FluentAI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Database - XAMPP MySQL
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "fluentai"
    
    # JWT Settings
    JWT_SECRET_KEY: str = "fluentai-super-secret-key-change-in-production-2024"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    
    # Encryption for API keys
    ENCRYPTION_KEY: str = "fluentai-encryption-key-32bytes!---"
    
    # CORS
    CORS_ORIGINS: list = ["http://localhost", "http://127.0.0.1", "http://localhost:80"]
    
    # XP Settings
    XP_PER_CORRECT_ANSWER: int = 10
    XP_BONUS_STREAK: int = 5
    XP_DAILY_LESSON_COMPLETE: int = 50
    XP_GRAMMAR_SPRINT_COMPLETE: int = 30
    XP_WORD_SPRINT_COMPLETE: int = 25
    XP_SPEAKING_SESSION: int = 40
    
    # CEFR Levels
    CEFR_LEVELS: list = ["A1", "A2", "B1", "B2", "C1", "C2"]
    
    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
