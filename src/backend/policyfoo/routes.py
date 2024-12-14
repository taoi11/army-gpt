from flask import request, jsonify
from typing import List, Dict
from src.backend.utils.logger import logger, truncate_llm_response
from src.backend.policyfoo.finder import policy_finder
from src.backend.policyfoo.reader import policy_reader
from src.backend.policyfoo.chat import chat_agent
from src.backend.llm.provider import Message
import re

async def join_responses(policy_contents: Dict[str, str]) -> str:
    """Simply join policy responses"""
    combined = ""
    
    for content in policy_contents.values():
        if content:
            # If content is an async generator, get its content
            if hasattr(content, '__aiter__'):
                try:
                    full_content = ""
                    async for chunk in content:
                        if chunk:
                            full_content += chunk
                    content = full_content
                except Exception as e:
                    logger.error(f"Error reading streaming content: {e}")
                    continue

            combined += f"\n{content}\n"
    
    return combined

def format_conversation_history(history: List[Dict]) -> List[Message]:
    """Format conversation history into Message objects"""
    try:
        # Take last 2 exchanges (4 messages)
        recent_history = history[-4:] if len(history) > 4 else history
        
        # Convert to Message objects, ensuring role and content are present
        messages = []
        for msg in recent_history:
            if msg.get('role') in ['user', 'assistant'] and msg.get('content'):
                messages.append(Message(
                    role=msg['role'],
                    content=msg['content'].split('\n\nReferences:')[0].strip()  # Remove citations if present
                ))
        
        # Log conversation history
        logger.debug(f"Formatted conversation history ({len(messages)} messages):")
        for msg in messages:
            logger.debug(f"- {msg.role}: {truncate_llm_response(msg.content)}")
            
        return messages
        
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
        history = data.get("conversation_history", [])
        
        # Log received conversation history
        logger.debug(f"Received conversation history ({len(history)} messages):")
        for msg in history:
            logger.debug(f"- {msg['role']}: {truncate_llm_response(msg.get('content', ''))}")
        
        # Validate query
        if not query:
            return jsonify({
                "error": "No query provided",
                "content": None
            }), 400
            
        # Format conversation history
        conversation_history = format_conversation_history(history)
            
        # Step 1: Find relevant policies
        logger.info(f"Finding relevant policies for query: {truncate_llm_response(query)}")
        policies = await policy_finder.find_relevant_policies(
            query=query,
            conversation_history=conversation_history,
            request_id=request_id
        )
        
        if not policies:
            logger.warning("No relevant policies found")
            return jsonify({
                "status": "success",
                "content": None
            })
            
        # Step 2: Get policy content
        logger.info(f"Reading {len(policies)} policies")
        policy_contents = await policy_reader.get_policy_content(
            policy_numbers=policies,
            query=query,
            conversation_history=conversation_history,
            request_id=request_id
        )
        
        if not policy_contents:
            logger.warning("Failed to extract policy content")
            return StreamingResponse(
                iter([
                    "<response><answer>I found some relevant policies but couldn't extract their content. Please try again.</answer><citations></citations><follow_up>Maybe try rephrasing your question?</follow_up></response>"
                ]),
                media_type="text/plain"
            )
        
        # Step 3: Join policy contents
        logger.debug("Joining policy contents")
        combined_content = await join_responses(policy_contents)
        logger.debug(f"Combined content: {truncate_llm_response(combined_content)}")
        
        # Step 4: Generate chat response using combined content
        logger.info("Generating chat response")
        response = await chat_agent.generate_response(
            query=request.content,
            policy_content=combined_content,
            conversation_history=conversation_history,
            request_id=request_id,
            temperature=request.temperature
        )
        
        # If response is an async generator, convert it to a string
        if hasattr(response, '__aiter__'):
            try:
                full_response = ""
                async for chunk in response:
                    full_response += chunk
                response = full_response
            except Exception as e:
                logger.error(f"Error reading streaming response: {e}")
                response = "<response><answer>Error processing streaming response</answer><citations></citations><follow_up></follow_up></response>"
        
        logger.debug(f"Final response: {truncate_llm_response(response)}")
        return jsonify({
            "status": "success",
            "content": response
        })
        
    except Exception as e:
        logger.error(f"Error in generate endpoint: {str(e)}")
        return jsonify({
            "error": "Internal server error",
            "content": None
        }), 500
