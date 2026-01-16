"""
Speech Service - Unified interface for speech processing
"""
from typing import Optional, Dict, Any, List
import logging
from .openai_service import OpenAIService
from .gemini_service import GeminiService

logger = logging.getLogger(__name__)


class SpeechService:
    """
    Unified speech service that routes to OpenAI or Gemini
    based on user preference and API key availability
    """
    
    def __init__(self, openai_key: Optional[str] = None, 
                 gemini_key: Optional[str] = None,
                 preferred_provider: str = "openai"):
        self.openai_service = OpenAIService(openai_key) if openai_key else None
        self.gemini_service = GeminiService(gemini_key) if gemini_key else None
        self.preferred = preferred_provider
    
    def _get_service(self):
        """Get the appropriate service based on preference and availability"""
        if self.preferred == "openai" and self.openai_service:
            return self.openai_service, "openai"
        elif self.preferred == "gemini" and self.gemini_service:
            return self.gemini_service, "gemini"
        elif self.openai_service:
            return self.openai_service, "openai"
        elif self.gemini_service:
            return self.gemini_service, "gemini"
        return None, None
    
    async def transcribe_audio(self, audio_data: bytes, 
                              language: str = "en") -> Dict[str, Any]:
        """
        Transcribe audio to text
        Note: Only OpenAI supports direct audio transcription
        """
        if self.openai_service:
            return await self.openai_service.transcribe_audio(audio_data, language)
        return {
            "success": False,
            "error": "OpenAI API key required for audio transcription",
            "text": ""
        }
    
    async def analyze_speech(self, transcript: str, context: str,
                           user_level: str) -> Dict[str, Any]:
        """Analyze speech for grammar, fluency, and vocabulary"""
        service, provider = self._get_service()
        if not service:
            return {
                "success": False,
                "error": "No AI service configured. Please add an API key in settings."
            }
        
        result = await service.analyze_speech(transcript, context, user_level)
        result["provider"] = provider
        return result
    
    async def generate_roleplay_response(self, scenario: str,
                                        conversation_history: List[Dict],
                                        user_level: str) -> Dict[str, Any]:
        """Generate AI response for roleplay"""
        service, provider = self._get_service()
        if not service:
            return {
                "success": False,
                "error": "No AI service configured. Please add an API key in settings."
            }
        
        result = await service.generate_roleplay_response(
            scenario, conversation_history, user_level
        )
        result["provider"] = provider
        return result
    
    async def generate_free_talk_response(self, user_message: str,
                                         conversation_history: List[Dict],
                                         user_level: str) -> Dict[str, Any]:
        """Generate AI response for free talk"""
        service, provider = self._get_service()
        if not service:
            return {
                "success": False,
                "error": "No AI service configured. Please add an API key in settings."
            }
        
        result = await service.generate_free_talk_response(
            user_message, conversation_history, user_level
        )
        result["provider"] = provider
        return result
    
    async def text_to_speech(self, text: str) -> Optional[bytes]:
        """Convert text to speech audio (OpenAI only)"""
        if self.openai_service:
            return await self.openai_service.generate_text_to_speech(text)
        return None
    
    def is_configured(self) -> Dict[str, bool]:
        """Check which services are configured"""
        return {
            "openai": self.openai_service is not None,
            "gemini": self.gemini_service is not None,
            "any": self.openai_service is not None or self.gemini_service is not None
        }
