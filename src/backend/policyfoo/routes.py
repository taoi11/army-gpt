from flask import request, jsonify, Response, stream_with_context
from src.backend.utils.logger import logger
from src.backend.policyfoo.finder import policy_finder
from src.backend.policyfoo.reader import policy_reader
from src.backend.policyfoo.chat import chat_agent
from src.backend.llm.provider import Message
from typing import List, Dict

def join_responses(policy_contents: Dict[str, str]) -> str:
    """Simply concatenate all policy responses"""
    return "\n".join(
        content 
        for content in policy_contents.values()
        if content
    )

def format_conversation_history(history: List[Dict]) -> List[Message]:
    """Format conversation history into Message objects"""
    try:
        # Take last 5 exchanges (10 messages - 5 user, 5 assistant)
        recent_history = history[-10:] if len(history) > 10 else history
        return [Message(**msg) for msg in recent_history]
    except Exception as e:
        logger.error(f"Error formatting conversation history: {str(e)}")
        return []

async def generate():
    """Main endpoint to handle policy-related agent activities"""
    try:
        # Get request data
        data = request.get_json()
        query = data.get("content")
        request_id = data.get("request_id")
        parallel_mode = data.get("parallel", True)  # Default to parallel processing
        history = data.get("conversation_history", [])
        
        # Validate query
        if not query:
            return jsonify({
                "error": "No query provided",
                "content": None
            }), 400
            
        # Format conversation history
        conversation_history = format_conversation_history(history)
            
        # Step 1: Find relevant policies
        logger.info(f"Finding relevant policies for query: {query}")
        policies = policy_finder.find_relevant_policies(
            query=query,
            conversation_history=conversation_history,
            request_id=request_id
        )
        
        if not policies:
            return jsonify({
                "status": "success",
                "content": None
            })
            
        # Step 2: Get policy content (parallel or sequential)
        logger.info(f"Reading {len(policies)} policies in {'parallel' if parallel_mode else 'sequential'} mode")
        policy_contents = await policy_reader.get_policy_content(
            policy_numbers=policies,
            query=query,
            parallel=parallel_mode,
            conversation_history=conversation_history,
            request_id=request_id
        )
        
        # Step 3: Join policy contents
        logger.info("Joining policy contents")
        combined_content = join_responses(policy_contents)
        
        # Step 4: Generate chat response (may be streaming)
        logger.info("Generating chat response")
        response = await chat_agent.generate_response(
            query=query,
            policy_content=combined_content,
            conversation_history=conversation_history,
            request_id=request_id
        )
        
        # Handle streaming vs non-streaming response
        if isinstance(response, str):
            # Non-streaming response
            return jsonify({
                "status": "success",
                "content": response
            })
        else:
            # Streaming response
            def generate_stream():
                try:
                    for chunk in response:
                        yield f"data: {chunk}\n\n"
                except Exception as e:
                    logger.error(f"Error in stream: {str(e)}")
                    yield f"data: Error in stream: {str(e)}\n\n"
                finally:
                    yield "data: [DONE]\n\n"
                    
            return Response(
                stream_with_context(generate_stream()),
                mimetype='text/event-stream'
            )
        
    except Exception as e:
        logger.error(f"Error in generate endpoint: {str(e)}")
        return jsonify({
            "error": "Internal server error",
            "content": None
        }), 500