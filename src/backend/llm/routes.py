from fastapi import APIRouter, Request, HTTPException, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from src.backend.utils.logger import logger
from src.backend.pacenote import PaceNoteAgent
from .keycheck import CREDITS_AVAILABLE
from src.backend.utils.rate_limit import rate_limiter
import uuid
import json

router = APIRouter(prefix="/llm")

class PaceNoteRequest(BaseModel):
    content: str
    temperature: Optional[float] = 0.1
    stream: Optional[bool] = True  # Default to streaming for Ollama

class PaceNoteResponse(BaseModel):
    note: str
    remaining_requests: dict

@router.get("/credits")
async def get_credits_status():
    """Return current credit status"""
    return {"credits_available": CREDITS_AVAILABLE}

@router.post("/pace-notes/generate")
async def generate_pace_note(
    request: PaceNoteRequest,
    client_request: Request
):
    """Generate a pace note"""
    try:
        # Generate request ID
        request_id = str(uuid.uuid4())
        client_request.state.request_id = request_id

        # Get rate limit info
        rate_limits = rate_limiter.get_remaining(client_request.client.host)

        if request.stream:
            # Generate streaming response
            stream = PaceNoteAgent.generate(
                content=request.content,
                temperature=request.temperature,
                request_id=request_id,
                stream=True
            )

            async def stream_generator():
                try:
                    async for chunk in stream:
                        # Format each chunk as a Server-Sent Event
                        yield f"data: {json.dumps({'note': chunk, 'remaining_requests': rate_limits})}\n\n"
                except Exception as e:
                    logger.error(f"Error in stream generator: {e}")
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"

            return StreamingResponse(
                stream_generator(),
                media_type="text/event-stream"
            )

        # Non-streaming response
        note = PaceNoteAgent.generate(
            content=request.content,
            temperature=request.temperature,
            request_id=request_id,
            stream=False
        )

        if note is None:
            raise HTTPException(
                status_code=503,
                detail="Failed to generate note. Please try again later."
            )

        return PaceNoteResponse(
            note=note,
            remaining_requests=rate_limits
        )

    except Exception as e:
        logger.error(f"Error in pace note generation endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        ) 

@router.post("/pace-notes/cancel")
async def cancel_generation(request: Request):
    """Cancel any ongoing generation for this client"""
    try:
        # Return 200 immediately to allow quick page refreshes
        return Response(status_code=200)
    except Exception as e:
        logger.error(f"Error in cancel endpoint: {str(e)}")
        return Response(status_code=200)  # Still return 200 to allow quick refresh 