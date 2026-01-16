"""
Speaking Router - UC9, UC10: AI Roleplay (Prepare Me) and Free Talk (Talk Loop)
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from typing import List, Optional
from datetime import datetime
import json
import logging
import base64

from utils.jwt_handler import get_current_user
from utils.encryption import decrypt_api_key
from database import get_db_cursor
from services.speech_service import SpeechService
from services.xp_calculator import XPCalculator

router = APIRouter()
logger = logging.getLogger(__name__)


# Roleplay scenarios
ROLEPLAY_SCENARIOS = {
    "A1": [
        {"id": "cafe", "title": "At the Café", "description": "Order coffee and snacks", "context": "You are a customer at a café. The waiter will take your order."},
        {"id": "shop", "title": "Shopping", "description": "Buy items at a store", "context": "You are shopping for clothes. Ask the shop assistant for help."},
        {"id": "directions", "title": "Asking Directions", "description": "Find your way around", "context": "You are lost in the city. Ask a local for directions to the train station."}
    ],
    "A2": [
        {"id": "hotel", "title": "Hotel Check-in", "description": "Book a room", "context": "You are checking into a hotel. Speak with the receptionist about your reservation."},
        {"id": "restaurant", "title": "Restaurant Order", "description": "Order a meal", "context": "You are at a restaurant. Order food and ask about ingredients."},
        {"id": "doctor", "title": "Doctor's Visit", "description": "Describe symptoms", "context": "You are visiting a doctor. Explain how you feel and ask for advice."}
    ],
    "B1": [
        {"id": "interview", "title": "Job Interview", "description": "Answer interview questions", "context": "You are in a job interview. Answer questions about your experience and skills."},
        {"id": "complaint", "title": "Making a Complaint", "description": "Resolve an issue", "context": "You bought a product that doesn't work. Explain the problem and ask for a refund."},
        {"id": "travel", "title": "Travel Agency", "description": "Plan a trip", "context": "You are at a travel agency. Discuss vacation options and book a trip."}
    ],
    "B2": [
        {"id": "debate", "title": "Friendly Debate", "description": "Express opinions", "context": "You are having a discussion about whether social media is good for society."},
        {"id": "presentation", "title": "Work Presentation", "description": "Present ideas", "context": "You are presenting a new project idea to your team. Explain your concept and answer questions."},
        {"id": "negotiate", "title": "Negotiation", "description": "Negotiate terms", "context": "You are negotiating the terms of a contract. Discuss price and conditions."}
    ],
    "C1": [
        {"id": "academic", "title": "Academic Discussion", "description": "Discuss research", "context": "You are discussing your research with a professor. Explain your methodology and findings."},
        {"id": "crisis", "title": "Crisis Management", "description": "Handle a crisis", "context": "You are a manager dealing with a company crisis. Communicate with your team and media."},
        {"id": "philosophy", "title": "Philosophical Discussion", "description": "Deep conversation", "context": "You are having a philosophical discussion about the meaning of success."}
    ]
}


async def _get_speech_service(user_id: int) -> SpeechService:
    """Get speech service configured with user's API keys"""
    with get_db_cursor() as cursor:
        cursor.execute(
            """SELECT openai_api_key, gemini_api_key, preferred_ai 
               FROM user_settings WHERE user_id = %s""",
            (user_id,)
        )
        settings = cursor.fetchone()
        
        if not settings:
            return SpeechService()
        
        openai_key = decrypt_api_key(settings["openai_api_key"]) if settings["openai_api_key"] else None
        gemini_key = decrypt_api_key(settings["gemini_api_key"]) if settings["gemini_api_key"] else None
        
        return SpeechService(
            openai_key=openai_key,
            gemini_key=gemini_key,
            preferred_provider=settings["preferred_ai"] or "openai"
        )


@router.get("/scenarios")
async def get_roleplay_scenarios(current_user: dict = Depends(get_current_user)):
    """
    Get available roleplay scenarios for user's level
    FR11: Voice-input conversational practice
    """
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                "SELECT cefr_level FROM users WHERE id = %s",
                (current_user["user_id"],)
            )
            user = cursor.fetchone()
            user_level = user["cefr_level"] or "A1"
            
            # Get scenarios for user's level and below
            available_scenarios = []
            level_order = ["A1", "A2", "B1", "B2", "C1", "C2"]
            user_index = level_order.index(user_level)
            
            for level in level_order[:user_index + 1]:
                if level in ROLEPLAY_SCENARIOS:
                    for scenario in ROLEPLAY_SCENARIOS[level]:
                        available_scenarios.append({
                            **scenario,
                            "level": level
                        })
            
            return {
                "user_level": user_level,
                "scenarios": available_scenarios
            }
    except Exception as e:
        logger.error(f"Get scenarios error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load scenarios")


@router.post("/roleplay/start")
async def start_roleplay(
    scenario_id: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Start a new roleplay session
    FR11: Start 5-turn conversational roleplay
    """
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                "SELECT cefr_level FROM users WHERE id = %s",
                (current_user["user_id"],)
            )
            user = cursor.fetchone()
            user_level = user["cefr_level"] or "A1"
        
        # Find scenario
        scenario = None
        for level_scenarios in ROLEPLAY_SCENARIOS.values():
            for s in level_scenarios:
                if s["id"] == scenario_id:
                    scenario = s
                    break
        
        if not scenario:
            raise HTTPException(status_code=404, detail="Scenario not found")
        
        # Get AI service
        service = await _get_speech_service(current_user["user_id"])
        
        # Generate initial AI response
        result = await service.generate_roleplay_response(
            scenario["context"],
            [],
            user_level
        )
        
        # Create session record
        session_id = int(datetime.now().timestamp() * 1000)
        
        with get_db_cursor() as cursor:
            cursor.execute(
                """INSERT INTO conversation_history 
                   (user_id, session_type, messages, scores, created_at)
                   VALUES (%s, 'roleplay', %s, '{}', %s)""",
                (
                    current_user["user_id"],
                    json.dumps([{
                        "is_ai": True,
                        "text": result.get("response", scenario["context"]),
                        "timestamp": datetime.now().isoformat()
                    }]),
                    datetime.now()
                )
            )
            session_id = cursor.lastrowid
        
        return {
            "session_id": session_id,
            "scenario": scenario,
            "ai_message": result.get("response", "Hello! How can I help you today?"),
            "hint": result.get("hint", ""),
            "turn": 1,
            "max_turns": 5,
            "provider": result.get("provider", "ai")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Start roleplay error: {e}")
        raise HTTPException(status_code=500, detail="Failed to start roleplay")


@router.post("/roleplay/respond")
async def roleplay_respond(
    session_id: int = Form(...),
    user_text: str = Form(None),
    audio: UploadFile = File(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Send response in roleplay and get AI reply
    FR12: Receive feedback on fluency, grammar, vocabulary
    """
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                "SELECT cefr_level FROM users WHERE id = %s",
                (current_user["user_id"],)
            )
            user = cursor.fetchone()
            user_level = user["cefr_level"] or "A1"
            
            # Get session
            cursor.execute(
                "SELECT messages FROM conversation_history WHERE id = %s AND user_id = %s",
                (session_id, current_user["user_id"])
            )
            session = cursor.fetchone()
            
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
        
        messages = json.loads(session["messages"]) if session["messages"] else []
        service = await _get_speech_service(current_user["user_id"])
        
        # Transcribe audio if provided
        transcript = user_text
        if audio and not user_text:
            audio_data = await audio.read()
            transcription = await service.transcribe_audio(audio_data)
            if transcription["success"]:
                transcript = transcription["text"]
            else:
                return {"error": "Failed to transcribe audio", "details": transcription.get("error")}
        
        if not transcript:
            raise HTTPException(status_code=400, detail="No input provided")
        
        # Add user message
        messages.append({
            "is_ai": False,
            "text": transcript,
            "timestamp": datetime.now().isoformat()
        })
        
        current_turn = sum(1 for m in messages if not m["is_ai"])
        
        # Analyze user's speech
        analysis = await service.analyze_speech(
            transcript,
            messages[-2]["text"] if len(messages) > 1 else "",
            user_level
        )
        
        # Generate AI response if not last turn
        ai_response = None
        if current_turn < 5:
            # Find scenario context from first AI message
            scenario_context = messages[0]["text"] if messages else ""
            ai_result = await service.generate_roleplay_response(
                scenario_context,
                messages,
                user_level
            )
            ai_response = ai_result.get("response", "")
            
            messages.append({
                "is_ai": True,
                "text": ai_response,
                "timestamp": datetime.now().isoformat()
            })
        
        # Update session
        with get_db_cursor() as cursor:
            scores = {
                "fluency": analysis.get("fluency_score", 0),
                "grammar": analysis.get("grammar_score", 0),
                "vocabulary": analysis.get("vocabulary_score", 0)
            }
            
            cursor.execute(
                """UPDATE conversation_history 
                   SET messages = %s, scores = %s
                   WHERE id = %s""",
                (json.dumps(messages), json.dumps(scores), session_id)
            )
            
            # Award XP if session complete
            if current_turn >= 5:
                xp = XPCalculator.calculate_speaking_xp(
                    analysis.get("fluency_score", 50),
                    analysis.get("grammar_score", 50),
                    analysis.get("vocabulary_score", 50),
                    len(messages) * 10
                )
                cursor.execute(
                    "UPDATE users SET xp_total = xp_total + %s WHERE id = %s",
                    (xp, current_user["user_id"])
                )
        
        return {
            "session_id": session_id,
            "user_message": transcript,
            "ai_message": ai_response,
            "turn": current_turn,
            "is_complete": current_turn >= 5,
            "analysis": {
                "fluency_score": analysis.get("fluency_score", 0),
                "grammar_score": analysis.get("grammar_score", 0),
                "vocabulary_score": analysis.get("vocabulary_score", 0),
                "feedback": analysis.get("overall_feedback", ""),
                "corrections": analysis.get("grammar_errors", []),
                "corrected_text": analysis.get("corrected_text", transcript)
            },
            "hint": ai_result.get("hint", "") if ai_response else "",
            "xp_earned": xp if current_turn >= 5 else 0
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Roleplay respond error: {e}")
        raise HTTPException(status_code=500, detail="Failed to process response")


@router.post("/freetalk/start")
async def start_free_talk(current_user: dict = Depends(get_current_user)):
    """
    Start a free talk session
    FR13: Unlimited open-ended conversation
    """
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                """INSERT INTO conversation_history 
                   (user_id, session_type, messages, scores, created_at)
                   VALUES (%s, 'freetalk', '[]', '{}', %s)""",
                (current_user["user_id"], datetime.now())
            )
            session_id = cursor.lastrowid
        
        return {
            "session_id": session_id,
            "message": "Free talk session started! Say anything to begin the conversation.",
            "tip": "Talk about your day, ask questions, or discuss any topic you're interested in."
        }
    except Exception as e:
        logger.error(f"Start free talk error: {e}")
        raise HTTPException(status_code=500, detail="Failed to start free talk")


@router.post("/freetalk/respond")
async def free_talk_respond(
    session_id: int = Form(...),
    user_text: str = Form(None),
    audio: UploadFile = File(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Send message in free talk and get AI response
    FR14, FR15: Real-time scoring and natural conversation
    """
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                "SELECT cefr_level FROM users WHERE id = %s",
                (current_user["user_id"],)
            )
            user = cursor.fetchone()
            user_level = user["cefr_level"] or "A1"
            
            cursor.execute(
                "SELECT messages, scores FROM conversation_history WHERE id = %s AND user_id = %s",
                (session_id, current_user["user_id"])
            )
            session = cursor.fetchone()
            
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
        
        messages = json.loads(session["messages"]) if session["messages"] else []
        cumulative_scores = json.loads(session["scores"]) if session["scores"] else {"fluency": [], "grammar": [], "vocabulary": []}
        
        service = await _get_speech_service(current_user["user_id"])
        
        # Transcribe audio if provided
        transcript = user_text
        if audio and not user_text:
            audio_data = await audio.read()
            transcription = await service.transcribe_audio(audio_data)
            if transcription["success"]:
                transcript = transcription["text"]
            else:
                return {"error": "Failed to transcribe audio"}
        
        if not transcript:
            raise HTTPException(status_code=400, detail="No input provided")
        
        # Add user message
        messages.append({
            "is_ai": False,
            "text": transcript,
            "timestamp": datetime.now().isoformat()
        })
        
        # Analyze and get response
        analysis = await service.analyze_speech(transcript, "", user_level)
        ai_result = await service.generate_free_talk_response(transcript, messages, user_level)
        
        ai_response = ai_result.get("response", "") 
        if ai_result.get("follow_up_question"):
            ai_response += " " + ai_result["follow_up_question"]
        
        messages.append({
            "is_ai": True,
            "text": ai_response,
            "timestamp": datetime.now().isoformat()
        })
        
        # Update cumulative scores
        if "fluency" not in cumulative_scores:
            cumulative_scores = {"fluency": [], "grammar": [], "vocabulary": []}
        
        cumulative_scores["fluency"].append(analysis.get("fluency_score", 0))
        cumulative_scores["grammar"].append(analysis.get("grammar_score", 0))
        cumulative_scores["vocabulary"].append(analysis.get("vocabulary_score", 0))
        
        # Calculate averages
        avg_scores = {
            "fluency": sum(cumulative_scores["fluency"]) / len(cumulative_scores["fluency"]),
            "grammar": sum(cumulative_scores["grammar"]) / len(cumulative_scores["grammar"]),
            "vocabulary": sum(cumulative_scores["vocabulary"]) / len(cumulative_scores["vocabulary"])
        }
        
        with get_db_cursor() as cursor:
            cursor.execute(
                """UPDATE conversation_history 
                   SET messages = %s, scores = %s
                   WHERE id = %s""",
                (json.dumps(messages), json.dumps(cumulative_scores), session_id)
            )
        
        return {
            "session_id": session_id,
            "user_message": transcript,
            "ai_message": ai_response,
            "correction": ai_result.get("correction"),
            "current_analysis": {
                "fluency": analysis.get("fluency_score", 0),
                "grammar": analysis.get("grammar_score", 0),
                "vocabulary": analysis.get("vocabulary_score", 0),
                "feedback": analysis.get("overall_feedback", ""),
                "corrections": analysis.get("grammar_errors", [])
            },
            "session_averages": avg_scores,
            "message_count": len([m for m in messages if not m["is_ai"]])
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Free talk respond error: {e}")
        raise HTTPException(status_code=500, detail="Failed to process response")


@router.post("/freetalk/end")
async def end_free_talk(
    session_id: int = Form(...),
    current_user: dict = Depends(get_current_user)
):
    """End free talk session and get final scores"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                "SELECT messages, scores, created_at FROM conversation_history WHERE id = %s AND user_id = %s",
                (session_id, current_user["user_id"])
            )
            session = cursor.fetchone()
            
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
            
            messages = json.loads(session["messages"]) if session["messages"] else []
            scores = json.loads(session["scores"]) if session["scores"] else {}
            
            # Calculate final scores
            final_scores = {
                "fluency": sum(scores.get("fluency", [0])) / max(len(scores.get("fluency", [1])), 1),
                "grammar": sum(scores.get("grammar", [0])) / max(len(scores.get("grammar", [1])), 1),
                "vocabulary": sum(scores.get("vocabulary", [0])) / max(len(scores.get("vocabulary", [1])), 1)
            }
            
            # Calculate duration
            start_time = session["created_at"]
            duration = (datetime.now() - start_time).seconds if start_time else 0
            
            # Award XP
            xp = XPCalculator.calculate_speaking_xp(
                final_scores["fluency"],
                final_scores["grammar"],
                final_scores["vocabulary"],
                duration
            )
            
            cursor.execute(
                "UPDATE users SET xp_total = xp_total + %s WHERE id = %s",
                (xp, current_user["user_id"])
            )
            
            user_messages = len([m for m in messages if not m["is_ai"]])
            
            return {
                "session_id": session_id,
                "duration_seconds": duration,
                "message_count": user_messages,
                "final_scores": final_scores,
                "xp_earned": xp,
                "summary": f"Great session! You exchanged {user_messages} messages over {duration // 60} minutes."
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"End free talk error: {e}")
        raise HTTPException(status_code=500, detail="Failed to end session")


@router.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Transcribe audio to text"""
    try:
        service = await _get_speech_service(current_user["user_id"])
        
        if not service.is_configured()["any"]:
            raise HTTPException(
                status_code=400,
                detail="No AI service configured. Please add an API key in settings."
            )
        
        audio_data = await audio.read()
        result = await service.transcribe_audio(audio_data)
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transcribe error: {e}")
        raise HTTPException(status_code=500, detail="Failed to transcribe audio")
