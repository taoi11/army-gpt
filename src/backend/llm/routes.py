from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional
from src.backend.utils.logger import logger
from src.backend.pacenote import pace_note_agent
from .keycheck import CREDITS_AVAILABLE

router = APIRouter(prefix="/llm")

class PaceNoteRequest(BaseModel):
    content: str
    temperature: Optional[float] = 0.1

class PaceNoteResponse(BaseModel):
    note: str
    remaining_requests: dict

@router.get("/credits")
async def get_credits_status():
    """Return current credit status"""
    return {"credits_available": CREDITS_AVAILABLE}

@router.post("/pace-notes/generate", response_model=PaceNoteResponse)
async def generate_pace_note(
    request: PaceNoteRequest,
    client_ip: str = None
):
    """Generate a pace note"""
    try:
        note = pace_note_agent.generate(
            content=request.content,
            temperature=request.temperature
        )

        if note is None:
            raise HTTPException(
                status_code=503,
                detail="Failed to generate note. Please try again later."
            )

        return PaceNoteResponse(
            note=note,
            remaining_requests={
                "hourly_remaining": 999,  # These will be overwritten by middleware
                "daily_remaining": 999
            }
        )

    except Exception as e:
        logger.error(f"Error in pace note generation endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        ) 