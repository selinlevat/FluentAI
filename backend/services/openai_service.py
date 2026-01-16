"""
OpenAI Service - GPT-4 and Whisper Integration
"""
import openai
from typing import Optional, Dict, Any, List
import json
import logging
import base64

logger = logging.getLogger(__name__)


class OpenAIService:
    """Service for OpenAI API interactions"""
    
    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key)
        self.model = "gpt-4o"  # Use GPT-4o for better performance
        self.whisper_model = "whisper-1"
    
    async def transcribe_audio(self, audio_data: bytes, language: str = "en") -> Dict[str, Any]:
        """
        Transcribe audio using Whisper
        
        Args:
            audio_data: Audio file bytes
            language: Target language code
        
        Returns:
            Dict with transcription and metadata
        """
        try:
            # Write audio to temp file-like object
            transcript = self.client.audio.transcriptions.create(
                model=self.whisper_model,
                file=("audio.webm", audio_data, "audio/webm"),
                language=language,
                response_format="verbose_json"
            )
            
            return {
                "success": True,
                "text": transcript.text,
                "duration": getattr(transcript, 'duration', 0),
                "language": language
            }
        except Exception as e:
            logger.error(f"Whisper transcription error: {e}")
            return {
                "success": False,
                "error": str(e),
                "text": ""
            }
    
    async def analyze_speech(self, transcript: str, context: str, 
                           user_level: str) -> Dict[str, Any]:
        """
        Analyze speech for fluency, grammar, and vocabulary
        
        Args:
            transcript: Transcribed speech text
            context: Conversation context or prompt
            user_level: User's CEFR level
        
        Returns:
            Analysis scores and feedback
        """
        system_prompt = f"""You are an expert English language tutor analyzing a student's spoken response.
The student is at {user_level} level (CEFR scale).

Analyze the following speech and provide scores and feedback in JSON format:
{{
    "fluency_score": 0-100,
    "grammar_score": 0-100,
    "vocabulary_score": 0-100,
    "pronunciation_notes": "notes on pronunciation patterns if detectable",
    "grammar_errors": ["list of grammar mistakes"],
    "vocabulary_suggestions": ["better word choices"],
    "overall_feedback": "constructive feedback message",
    "corrected_text": "the text with corrections applied"
}}

Be encouraging but accurate. Adjust expectations based on their CEFR level."""

        user_prompt = f"""Context/Prompt: {context}

Student's Response: {transcript}

Provide your analysis in JSON format."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            
            result = json.loads(response.choices[0].message.content)
            result["success"] = True
            return result
            
        except Exception as e:
            logger.error(f"Speech analysis error: {e}")
            return {
                "success": False,
                "error": str(e),
                "fluency_score": 0,
                "grammar_score": 0,
                "vocabulary_score": 0
            }
    
    async def generate_roleplay_response(self, scenario: str, 
                                        conversation_history: List[Dict],
                                        user_level: str) -> Dict[str, Any]:
        """
        Generate AI response for roleplay conversation
        
        Args:
            scenario: Roleplay scenario description
            conversation_history: Previous messages in conversation
            user_level: User's CEFR level
        
        Returns:
            AI response with coaching hints
        """
        system_prompt = f"""You are playing a role in a language learning scenario.
Adapt your language complexity to {user_level} level (CEFR scale).

Scenario: {scenario}

Guidelines:
- Stay in character
- Use natural conversational English
- Adjust vocabulary complexity for {user_level} level
- If the student makes errors, subtly model correct usage
- Keep responses concise (2-3 sentences max)
- End with something that prompts a response from the student

Respond in JSON format:
{{
    "response": "your in-character response",
    "hint": "optional hint for the student on how to respond",
    "vocabulary_highlight": ["new/useful words used"]
}}"""

        messages = [{"role": "system", "content": system_prompt}]
        
        for msg in conversation_history:
            role = "assistant" if msg.get("is_ai") else "user"
            messages.append({"role": role, "content": msg.get("text", "")})
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=300
            )
            
            result = json.loads(response.choices[0].message.content)
            result["success"] = True
            return result
            
        except Exception as e:
            logger.error(f"Roleplay generation error: {e}")
            return {
                "success": False,
                "error": str(e),
                "response": "I'm sorry, I couldn't generate a response. Please try again."
            }
    
    async def generate_free_talk_response(self, user_message: str,
                                         conversation_history: List[Dict],
                                         user_level: str) -> Dict[str, Any]:
        """
        Generate response for free talk session
        """
        system_prompt = f"""You are a friendly English conversation partner.
The student is at {user_level} level (CEFR scale).

Guidelines:
- Be natural and conversational
- Show interest in what the student says
- Ask follow-up questions to keep conversation flowing
- Gently correct major errors by modeling correct usage
- Use vocabulary appropriate for their level

Respond in JSON format:
{{
    "response": "your conversational response",
    "follow_up_question": "a question to continue the conversation",
    "correction": "subtle correction if needed, null otherwise"
}}"""

        messages = [{"role": "system", "content": system_prompt}]
        
        for msg in conversation_history[-10:]:  # Last 10 messages
            role = "assistant" if msg.get("is_ai") else "user"
            messages.append({"role": role, "content": msg.get("text", "")})
        
        messages.append({"role": "user", "content": user_message})
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.8,
                max_tokens=200
            )
            
            result = json.loads(response.choices[0].message.content)
            result["success"] = True
            return result
            
        except Exception as e:
            logger.error(f"Free talk generation error: {e}")
            return {
                "success": False,
                "error": str(e),
                "response": "That's interesting! Could you tell me more?"
            }
    
    async def generate_text_to_speech(self, text: str, voice: str = "alloy") -> Optional[bytes]:
        """
        Generate speech audio from text
        
        Args:
            text: Text to convert to speech
            voice: Voice to use (alloy, echo, fable, onyx, nova, shimmer)
        
        Returns:
            Audio bytes or None
        """
        try:
            response = self.client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=text
            )
            return response.content
        except Exception as e:
            logger.error(f"TTS generation error: {e}")
            return None
