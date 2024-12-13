from flask import request, jsonify
from src.backend.utils.logger import logger, truncate_llm_response
from src.backend.policyfoo.finder import policy_finder
from src.backend.policyfoo.reader import policy_reader
from src.backend.policyfoo.chat import chat_agent
from src.backend.llm.provider import Message
from typing import List, Dict

def join_responses(policy_contents: Dict[str, str]) -> str:
    """Join policy responses while preserving XML structure"""
    # Combine all policy extracts into one XML structure
    combined = "<policy_extracts>\n"
    
    for policy_number, content in policy_contents.items():
        if content:
            # Add policy number as attribute if not in the content
            if "<policy_number>" not in content:
                combined += f"<policy_extract policy_number='{policy_number}'>\n{content}\n</policy_extract>\n"
            else:
                combined += f"{content}\n"
    
    combined += "</policy_extracts>"
    return combined

def format_conversation_history(history: List[Dict]) -> List[Message]:
    """Format conversation history into Message objects"""
    try:
        # Take last 5 exchanges (10 messages - 5 user, 5 assistant)
        recent_history = history[-10:] if len(history) > 10 else history
        
        # Convert to Message objects, ensuring role and content are present
        messages = []
        for msg in recent_history:
            if msg.get('role') in ['user', 'assistant'] and msg.get('content'):
                messages.append(Message(
                    role=msg['role'],
                    content=msg['content']
                ))
        
        # Log conversation history
        logger.debug(f"Using conversation history ({len(messages)} messages):")
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
            logger.debug(f"- {msg['role']}: {truncate_llm_response(msg['content'])}")
        
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
        
        # Step 3: Join policy contents
        logger.debug("Joining policy contents")
        combined_content = join_responses(policy_contents)
        logger.debug(f"Combined content: {truncate_llm_response(combined_content)}")
        
        # Step 4: Generate chat response
        logger.info("Generating chat response")
        response = await chat_agent.generate_response(
            query=query,
            policy_content=combined_content,
            conversation_history=conversation_history,
            request_id=request_id
        )
        
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