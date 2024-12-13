from fastapi import APIRouter, Request, HTTPException, Response
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
from src.backend.utils.logger import logger
from src.backend.pacenote import PaceNoteAgent
from .keycheck import credits_checker
from src.backend.utils.rate_limit import rate_limiter
from src.backend.llm.provider import Message  # Use our own Message class
import uuid
import json
import os

router = APIRouter(prefix="/llm")

class PaceNoteRequest(BaseModel):
    content: str
    temperature: Optional[float] = 0.1
    stream: Optional[bool] = True  # Default to streaming for Ollama

class PaceNoteResponse(BaseModel):
    note: str
    remaining_requests: dict

class PolicyFooRequest(BaseModel):
    content: str
    conversation_history: Optional[List[Dict[str, str]]] = []  # Add conversation history field
    temperature: Optional[float] = 0.1
    stream: Optional[bool] = False  # Default to non-streaming for policy-foo

@router.get("/credits")
async def check_credits():
    """Check if we have credits available"""
    return {"credits_available": credits_checker.has_credits}

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

@router.post("/policyfoo/generate")
async def generate_policy_response(
    request: PolicyFooRequest,
    client_request: Request
):
    """Generate policy response using the policy finder and chat agents"""
    try:
        # Get client IP and generate request ID
        client_ip = client_request.client.host
        request_id = str(uuid.uuid4())
        
        # Initialize response
        response = None
        remaining = {"hourly_remaining": 0, "daily_remaining": 0}
        
        # Import policy agents here to avoid circular imports
        from src.backend.policyfoo.finder import policy_finder
        from src.backend.policyfoo.reader import policy_reader
        from src.backend.policyfoo.chat import chat_agent
        
        # Format conversation history using our Message class
        conversation_history = [
            Message(role=msg["role"], content=msg["content"])
            for msg in request.conversation_history
        ] if request.conversation_history else []
        
        # Step 1: Find relevant policies
        policy_refs = await policy_finder.find_relevant_policies(
            query=request.content,
            conversation_history=conversation_history,
            request_id=request_id
        )
        
        if not policy_refs:
            logger.warning("No relevant policies found")
            return JSONResponse(
                content={
                    "content": "<response><answer>I couldn't find any relevant policies for your query. Could you please rephrase or provide more details?</answer><citations></citations><follow_up>Try asking about a specific policy area?</follow_up></response>",
                    "remaining_requests": remaining
                },
                headers={
                    "X-RateLimit-Remaining-Hour": str(remaining["hourly_remaining"]),
                    "X-RateLimit-Remaining-Day": str(remaining["daily_remaining"])
                }
            )
        
        # Step 2: Get policy content with parallel processing
        policy_contents = await policy_reader.get_policy_content(
            policy_numbers=policy_refs,
            query=request.content,
            conversation_history=conversation_history,
            request_id=request_id,
            temperature=request.temperature,
            parallel=True
        )
        
        if not policy_contents:
            logger.warning("Failed to extract policy content")
            return JSONResponse(
                content={
                    "content": "<response><answer>I found some relevant policies but couldn't extract their content. Please try again.</answer><citations></citations><follow_up>Maybe try rephrasing your question?</follow_up></response>",
                    "remaining_requests": remaining
                },
                headers={
                    "X-RateLimit-Remaining-Hour": str(remaining["hourly_remaining"]),
                    "X-RateLimit-Remaining-Day": str(remaining["daily_remaining"])
                }
            )
        
        # Step 3: Generate chat response using first policy content
        first_policy = next(iter(policy_contents.values()))
        response = await chat_agent.generate_response(
            query=request.content,
            policy_content=first_policy,
            conversation_history=conversation_history,
            request_id=request_id,
            temperature=request.temperature
        )
        
        # Only check rate limits if we got a successful response and using OpenRouter
        if credits_checker.has_credits and response and not isinstance(response, str):
            # is_allowed() will add the request if allowed
            if not rate_limiter.is_allowed(client_ip, request_id):
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded"
                )
            remaining = rate_limiter.get_remaining(client_ip)
        
        return JSONResponse(
            content={
                "content": response if response else "<response><answer>Sorry, I encountered an error processing your request. Please try again.</answer><citations></citations><follow_up></follow_up></response>",
                "remaining_requests": remaining
            },
            headers={
                "X-RateLimit-Remaining-Hour": str(remaining["hourly_remaining"]),
                "X-RateLimit-Remaining-Day": str(remaining["daily_remaining"])
            }
        )
        
    except Exception as e:
        logger.error(f"Error in generate endpoint: {str(e)}")
        return JSONResponse(
            content={
                "content": f"<response><answer>An error occurred: {str(e)}</answer><citations></citations><follow_up></follow_up></response>",
                "remaining_requests": {"hourly_remaining": 0, "daily_remaining": 0}
            },
            status_code=500
        )