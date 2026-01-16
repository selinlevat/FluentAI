"""
Google Gemini Service - AI Integration
"""
import google.generativeai as genai
from typing import Optional, Dict, Any, List
import json
import logging

logger = logging.getLogger(__name__)


class GeminiService:
    """Service for Google Gemini API interactions"""
    
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        self.vision_model = genai.GenerativeModel('gemini-pro-vision')
    
    async def analyze_speech(self, transcript: str, context: str,
                           user_level: str) -> Dict[str, Any]:
        """
        Analyze speech for fluency, grammar, and vocabulary using Gemini
        
        Args:
            transcript: Transcribed speech text
            context: Conversation context or prompt
            user_level: User's CEFR level
        
        Returns:
            Analysis scores and feedback
        """
        prompt = f"""You are an expert English language tutor analyzing a student's spoken response.
The student is at {user_level} level (CEFR scale).

Context/Prompt: {context}
Student's Response: {transcript}

Analyze the response and provide scores and feedback. Return ONLY valid JSON in this exact format:
{{
    "fluency_score": <number 0-100>,
    "grammar_score": <number 0-100>,
    "vocabulary_score": <number 0-100>,
    "pronunciation_notes": "<notes on pronunciation patterns if detectable>",
    "grammar_errors": ["<list of grammar mistakes>"],
    "vocabulary_suggestions": ["<better word choices>"],
    "overall_feedback": "<constructive feedback message>",
    "corrected_text": "<the text with corrections applied>"
}}

Be encouraging but accurate. Adjust expectations based on their CEFR level."""

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=1000
                )
            )
            
            # Parse JSON from response
            response_text = response.text
            # Extract JSON if wrapped in markdown
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            
            result = json.loads(response_text.strip())
            result["success"] = True
            return result
            
        except Exception as e:
            logger.error(f"Gemini speech analysis error: {e}")
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
        Generate AI response for roleplay conversation using Gemini
        """
        history_text = "\n".join([
            f"{'AI' if msg.get('is_ai') else 'Student'}: {msg.get('text', '')}"
            for msg in conversation_history[-6:]
        ])
        
        prompt = f"""You are playing a role in a language learning scenario.
Adapt your language complexity to {user_level} level (CEFR scale).

Scenario: {scenario}

Conversation so far:
{history_text}

Guidelines:
- Stay in character for the scenario
- Use natural conversational English
- Adjust vocabulary complexity for {user_level} level
- Keep responses concise (2-3 sentences max)
- End with something that prompts a response

Return ONLY valid JSON in this exact format:
{{
    "response": "<your in-character response>",
    "hint": "<optional hint for the student on how to respond>",
    "vocabulary_highlight": ["<new/useful words used>"]
}}"""

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=300
                )
            )
            
            response_text = response.text
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            
            result = json.loads(response_text.strip())
            result["success"] = True
            return result
            
        except Exception as e:
            logger.error(f"Gemini roleplay error: {e}")
            return {
                "success": False,
                "error": str(e),
                "response": "I'm sorry, I couldn't generate a response. Please try again."
            }
    
    async def generate_free_talk_response(self, user_message: str,
                                         conversation_history: List[Dict],
                                         user_level: str) -> Dict[str, Any]:
        """
        Generate response for free talk session using Gemini
        """
        history_text = "\n".join([
            f"{'AI' if msg.get('is_ai') else 'Student'}: {msg.get('text', '')}"
            for msg in conversation_history[-8:]
        ])
        
        prompt = f"""You are a friendly English conversation partner.
The student is at {user_level} level (CEFR scale).

Conversation so far:
{history_text}

Student's new message: {user_message}

Guidelines:
- Be natural and conversational
- Show interest in what the student says
- Ask follow-up questions
- Use vocabulary appropriate for their level

Return ONLY valid JSON in this exact format:
{{
    "response": "<your conversational response>",
    "follow_up_question": "<a question to continue the conversation>",
    "correction": "<subtle correction if needed, or null>"
}}"""

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.8,
                    max_output_tokens=200
                )
            )
            
            response_text = response.text
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            
            result = json.loads(response_text.strip())
            result["success"] = True
            return result
            
        except Exception as e:
            logger.error(f"Gemini free talk error: {e}")
            return {
                "success": False,
                "error": str(e),
                "response": "That's interesting! Could you tell me more?"
            }
    
    async def generate_grammar_explanation(self, grammar_point: str,
                                          user_level: str) -> Dict[str, Any]:
        """
        Generate grammar explanation appropriate for user level
        """
        prompt = f"""Explain the following English grammar point to a student at {user_level} level (CEFR scale).

Grammar point: {grammar_point}

Provide:
1. A clear, simple explanation
2. 2-3 example sentences
3. Common mistakes to avoid

Return ONLY valid JSON in this exact format:
{{
    "explanation": "<clear explanation>",
    "examples": ["<example 1>", "<example 2>", "<example 3>"],
    "common_mistakes": ["<mistake to avoid>"],
    "tip": "<helpful tip>"
}}"""

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=500
                )
            )
            
            response_text = response.text
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            
            result = json.loads(response_text.strip())
            result["success"] = True
            return result
            
        except Exception as e:
            logger.error(f"Gemini grammar explanation error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
