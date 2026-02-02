"""Chat API with agent orchestration."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import structlog

from models import ChatRequest, ChatResponse
from agent.orchestrator import AgentOrchestrator
from database import get_db

logger = structlog.get_logger()
router = APIRouter()


class TroubleshootAnswerRequest(BaseModel):
    session_id: str
    flow_id: str
    step: int
    answer: str
    context: dict = {}


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint.
    
    Processes user messages through the agent orchestrator.
    """
    try:
        logger.info("Chat request", session_id=request.session_id, message=request.message[:100])
        
        # Get or create session
        db = get_db()
        session_result = db.table("chat_sessions").select("*").eq("id", request.session_id).execute()
        
        if not session_result.data:
            # Create new session
            session_data = {
                "id": request.session_id,
                "appliance_type": request.context.get("appliance") if request.context else None,
                "model_number": request.context.get("modelNumber") if request.context else None,
            }
            db.table("chat_sessions").insert(session_data).execute()
        
        # Save user message
        db.table("chat_messages").insert({
            "session_id": request.session_id,
            "role": "user",
            "content": request.message,
        }).execute()
        
        # Process through agent
        orchestrator = AgentOrchestrator()
        response = await orchestrator.process_message(request)
        
        # Save assistant message
        db.table("chat_messages").insert({
            "session_id": request.session_id,
            "role": "assistant",
            "content": response.assistant_text,
        }).execute()
        
        # Update session context if needed
        if request.context and request.context.get("modelNumber"):
            db.table("chat_sessions").update({
                "model_number": request.context["modelNumber"]
            }).eq("id", request.session_id).execute()
        
        return response
        
    except Exception as e:
        logger.error("Chat failed", session_id=request.session_id, error=str(e))
        raise HTTPException(status_code=500, detail="Chat processing failed")


@router.post("/troubleshoot-answer", response_model=ChatResponse)
async def troubleshoot_answer(request: TroubleshootAnswerRequest):
    """
    Handle troubleshooting flow answers with branching logic.
    
    This endpoint processes user answers to troubleshooting questions
    and returns the next question or final recommendation based on
    the decision tree logic.
    """
    try:
        logger.info(
            "Troubleshoot answer", 
            session_id=request.session_id, 
            flow=request.flow_id,
            step=request.step,
            answer=request.answer
        )
        
        # Get session context
        db = get_db()
        session_result = db.table("chat_sessions").select("*").eq("id", request.session_id).execute()
        
        context = request.context or {}
        if session_result.data:
            session = session_result.data[0]
            context["appliance"] = session.get("appliance_type", "refrigerator")
            context["modelNumber"] = session.get("model_number")
        
        # Save user answer as a message
        db.table("chat_messages").insert({
            "session_id": request.session_id,
            "role": "user",
            "content": f"Answer: {request.answer}",
        }).execute()
        
        # Process through orchestrator
        orchestrator = AgentOrchestrator()
        response = await orchestrator._handle_troubleshoot_answer(
            request.flow_id,
            request.answer,
            request.step,
            context
        )
        
        # Save assistant response
        db.table("chat_messages").insert({
            "session_id": request.session_id,
            "role": "assistant",
            "content": response.assistant_text,
        }).execute()
        
        return response
        
    except Exception as e:
        logger.error(
            "Troubleshoot answer failed", 
            session_id=request.session_id, 
            error=str(e)
        )
        raise HTTPException(status_code=500, detail="Troubleshooting processing failed")
