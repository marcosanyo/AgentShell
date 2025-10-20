#!/usr/bin/env python3
"""
AWS Lambda function for Alexa Skill - AgentShell Trigger

Usage:
  "Alexa, call the agent shell in the living room"
  → Lambda → AgentCore Runtime (Bedrock AgentCore)
"""

import boto3
import json
import logging
import os
import uuid
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AgentCore Runtime ARN (must be set via environment variable)
AGENT_RUNTIME_ARN = os.environ.get("BEDROCK_AGENT_RUNTIME_ARN")
if not AGENT_RUNTIME_ARN:
    raise ValueError("BEDROCK_AGENT_RUNTIME_ARN environment variable must be set")

# Room to camera mapping (set from environment variable)
ROOM_CAMERA_MAPPING = {
    "living room": os.environ.get("LIVING_ROOM_CAMERA", "camera1"),
    "living": os.environ.get("LIVING_ROOM_CAMERA", "camera1"),
    "lounge": os.environ.get("LIVING_ROOM_CAMERA", "camera1"),
    "main room": os.environ.get("LIVING_ROOM_CAMERA", "camera1"),
    "entrance": os.environ.get("ENTRANCE_CAMERA", "camera2"),
    "entry": os.environ.get("ENTRANCE_CAMERA", "camera2"),
    "front door": os.environ.get("ENTRANCE_CAMERA", "camera2"),
}

# Bedrock AgentCore client
agent_core_client = boto3.client('bedrock-agentcore', region_name='ap-northeast-1')

def lambda_handler(event, context):
    """
    Alexa Skill request handler.
    
    Args:
        event: Request from Alexa
        context: Lambda execution context
    """
    logger.info(f"Received event: {json.dumps(event)}")
    
    request_type = event["request"]["type"]
    
    if request_type == "LaunchRequest":
        return handle_launch_request(event)
    elif request_type == "IntentRequest":
        return handle_intent_request(event)
    elif request_type == "SessionEndedRequest":
        return handle_session_ended_request(event)
    else:
        return build_response("Sorry, I didn't understand that.")

def handle_launch_request(event):
    """
    When skill is launched (e.g., "Alexa, open agent shell")
    """
    speech_text = "Agent shell activated. Which room's camera would you like to access? Say living room or entrance."
    
    return build_response(
        speech_text,
        should_end_session=False,
        reprompt_text="Please say living room or entrance."
    )

def handle_intent_request(event):
    """
    Intent processing
    """
    intent_name = event["request"]["intent"]["name"]
    
    if intent_name == "CallAgentIntent":
        return handle_call_agent_intent(event)
    elif intent_name == "AMAZON.HelpIntent":
        return handle_help_intent()
    elif intent_name == "AMAZON.CancelIntent" or intent_name == "AMAZON.StopIntent":
        return handle_cancel_intent()
    else:
        return build_response("Sorry, that operation is not supported.")

def handle_call_agent_intent(event):
    """
    "Call the agent shell in the living room" intent
    """
    # Get slot values
    slots = event["request"]["intent"].get("slots", {})
    room_slot = slots.get("Room", {})
    
    # Check if Room slot has a value
    if not room_slot or "value" not in room_slot:
        logger.warning(f"Room slot missing or empty: {room_slot}")
        # Delegate back to Alexa to collect the slot
        return delegate_dialog(event)
    
    room = room_slot.get("value", "").lower()
    
    # Normalize room name (handle "the living room" → "living room")
    room = room.replace("the ", "")
    
    logger.info(f"Calling AgentCore for room: {room}")
    logger.info(f"Room slot details: {room_slot}")
    
    # Invoke AgentCore Runtime and wait for confirmation
    try:
        success, message = invoke_agentcore_async(room)
        
        if success:
            # Return success response to Alexa
            speech_text = f"Agent shell started for the {room}. The camera will greet you shortly."
        else:
            # Return error message from AgentCore invocation
            speech_text = f"Sorry, I couldn't start the agent shell. {message}"
            logger.error(f"AgentCore invocation failed: {message}")
    
    except Exception as e:
        logger.exception("Error invoking AgentCore")
        speech_text = "Sorry, there was a problem starting the agent shell. Please try again later."
    
    return build_response(speech_text, should_end_session=True)

def handle_help_intent():
    """
    Help intent
    """
    speech_text = (
        "Agent shell is a voice-based interactive system that uses cameras. "
        "You can say: start agent shell in the living room or entrance."
    )
    return build_response(speech_text, should_end_session=False)

def handle_cancel_intent():
    """
    Cancel/Stop intent
    """
    return build_response("Goodbye.", should_end_session=True)

def handle_session_ended_request(event):
    """
    Session ended
    """
    return build_response("", should_end_session=True)

def invoke_agentcore_async(room: str) -> tuple[bool, str]:
    """
    Invoke AgentCore Runtime and confirm it started successfully.
    
    Args:
        room: Room name (e.g., "living room", "entrance")
    
    Returns:
        tuple[bool, str]: (success, message)
            - success: True if AgentCore invocation was successful
            - message: Error message if failed, empty string if successful
    """
    # Get camera ID from room name
    camera_id = ROOM_CAMERA_MAPPING.get(room.lower(), "camera1")
    
    # Validate camera ID exists
    if camera_id not in ["camera1", "camera2"]:
        logger.error(f"Invalid camera_id: {camera_id}")
        return False, f"Camera for {room} is not configured."
    
    # Generate session ID (must be 33+ characters)
    session_id = f"alexa-{room}-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:10]}"
    
    # Build prompt (with explicit camera ID)
    prompt = f"""Activated via Alexa.

Room: {room}
Target Camera: {camera_id}

Start a conversation session.

1. First greet the user: "How can I help you?" (using {camera_id}_speak_on_camera tool)
2. Enter LISTEN mode and capture audio input (using {camera_id}_listen_on_camera tool)
3. Respond appropriately to what was heard (using {camera_id}_speak_on_camera tool)
4. Return to step 2 and continue the conversation loop

Important:
- Always use {camera_id} tools exclusively ({camera_id}_speak_on_camera, {camera_id}_listen_on_camera, etc.)
- Use a friendly and natural tone
- Execute listen_on_camera and speak_on_camera alternately"""
    
    # Prepare payload
    payload = json.dumps({"prompt": prompt}).encode('utf-8')
    
    logger.info(f"Invoking AgentCore Runtime: {AGENT_RUNTIME_ARN}")
    logger.info(f"Room: {room}, Camera: {camera_id}")
    logger.info(f"Session ID: {session_id}")
    logger.info(f"Prompt: {prompt[:150]}...")
    
    try:
        # Invoke AgentCore Runtime
        response = agent_core_client.invoke_agent_runtime(
            agentRuntimeArn=AGENT_RUNTIME_ARN,
            contentType="application/json",
            payload=payload,
            traceId=session_id,
        )
        
        # Check response status
        status_code = response.get('ResponseMetadata', {}).get('HTTPStatusCode')
        
        if status_code == 200:
            logger.info(f"AgentCore invocation successful. Session: {session_id}")
            logger.info(f"Response metadata: {response.get('ResponseMetadata', {})}")
            
            # Verify response stream exists
            if 'response' in response:
                logger.info("AgentCore streaming started (fire-and-forget mode)")
                return True, ""
            else:
                logger.warning("AgentCore response missing 'response' field")
                return False, "The agent started but response stream is unavailable."
        else:
            logger.error(f"AgentCore returned unexpected status: {status_code}")
            return False, f"Service returned status code {status_code}."
        
    except agent_core_client.exceptions.ResourceNotFoundException:
        logger.exception("AgentCore Runtime not found")
        return False, "Agent runtime is not available."
    except agent_core_client.exceptions.AccessDeniedException:
        logger.exception("Access denied to AgentCore")
        return False, "Permission denied to access agent runtime."
    except agent_core_client.exceptions.ThrottlingException:
        logger.exception("AgentCore throttling")
        return False, "Service is busy. Please try again in a moment."
    except Exception as e:
        logger.exception(f"Failed to invoke AgentCore: {e}")
        return False, f"An error occurred: {str(e)[:100]}"

def delegate_dialog(event) -> dict:
    """
    Delegate dialog back to Alexa to collect missing slots
    
    Args:
        event: Original Alexa event
    
    Returns:
        Dialog delegation response
    """
    logger.info("Delegating dialog to Alexa to collect slots")
    
    return {
        "version": "1.0",
        "response": {
            "directives": [
                {
                    "type": "Dialog.Delegate",
                    "updatedIntent": event["request"]["intent"]
                }
            ],
            "shouldEndSession": False
        }
    }

def build_response(
    speech_text: str,
    should_end_session: bool = True,
    reprompt_text: str = None
) -> dict:
    """
    Build Alexa response
    
    Args:
        speech_text: Text for Alexa to speak
        should_end_session: Whether to end the session
        reprompt_text: Text to speak if user doesn't respond
    """
    response = {
        "version": "1.0",
        "response": {
            "outputSpeech": {
                "type": "PlainText",
                "text": speech_text
            },
            "shouldEndSession": should_end_session
        }
    }
    
    if reprompt_text and not should_end_session:
        response["response"]["reprompt"] = {
            "outputSpeech": {
                "type": "PlainText",
                "text": reprompt_text
            }
        }
    
    return response
