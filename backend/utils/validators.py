"""
Input Validators
"""
import re
from typing import Tuple


def validate_email(email: str) -> Tuple[bool, str]:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if re.match(pattern, email):
        return True, ""
    return False, "Invalid email format"


def validate_password(password: str) -> Tuple[bool, str]:
    """
    Validate password strength
    - At least 6 characters
    - At least one letter
    - At least one number
    """
    if len(password) < 6:
        return False, "Password must be at least 6 characters long"
    
    if not re.search(r'[A-Za-z]', password):
        return False, "Password must contain at least one letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    
    return True, ""


def validate_cefr_level(level: str) -> bool:
    """Validate CEFR level"""
    valid_levels = ["A1", "A2", "B1", "B2", "C1", "C2"]
    return level.upper() in valid_levels


def sanitize_string(text: str) -> str:
    """Basic string sanitization"""
    # Remove any HTML tags
    clean = re.sub(r'<[^>]+>', '', text)
    # Remove multiple spaces
    clean = re.sub(r'\s+', ' ', clean)
    return clean.strip()
