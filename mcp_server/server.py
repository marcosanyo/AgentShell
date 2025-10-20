#!/usr/bin/env python3
"""Working Tapo MCP Server - Proven functionality only"""

import asyncio
import base64
import json
import logging
import os
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Union

# Add project root to sys.path to allow absolute imports
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import aiohttp
import boto3
from dotenv import load_dotenv
from fastmcp import FastMCP
from onvif import ONVIFCamera

from camera_utils.ptz import PTZController
from camera_utils.aws_tts import EmotionalTTS
from camera_utils.aws_stt import AWSTranscribeClient

# Load environment variables from .env file
config_path = project_root / ".env"
load_dotenv(dotenv_path=config_path)

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get camera profile from environment (camera1, camera2, etc.)
CAMERA_PROFILE = os.getenv("CAMERA_PROFILE", "").lower()

# Camera configuration from environment
# If CAMERA_PROFILE is set (e.g., "camera1"), use profile-specific env vars
# Otherwise, fall back to generic CAMERA_* env vars
if CAMERA_PROFILE:
    profile_prefix = CAMERA_PROFILE.upper().replace("CAMERA", "CAMERA")
    CAMERA_CONFIG = {
        "ip": os.getenv(f"{profile_prefix}_IP", os.getenv("CAMERA_IP", "192.168.11.34")),
        "port": int(os.getenv(f"{profile_prefix}_PORT", os.getenv("CAMERA_PORT", "2020"))),
        "user": os.getenv(f"{profile_prefix}_USER", os.getenv("CAMERA_USER", "admin")),
        "password": os.getenv(f"{profile_prefix}_PASSWORD", os.getenv("CAMERA_PASSWORD", "")),
    }
    GO2RTC_CAMERA_STREAM_NAME = os.getenv(f"{profile_prefix}_STREAM_NAME", os.getenv("GO2RTC_CAMERA_STREAM_NAME", "tapo_cam"))
    # Set default voice based on camera profile
    if CAMERA_PROFILE == "camera1":
        DEFAULT_VOICE = "Matthew"  # Male voice for Camera 1
    elif CAMERA_PROFILE == "camera2":
        DEFAULT_VOICE = "Joanna"   # Female voice for Camera 2
    else:
        DEFAULT_VOICE = "Joanna"   # Fallback
    logger.info(f"Using camera profile: {CAMERA_PROFILE} with default voice: {DEFAULT_VOICE}")
else:
    CAMERA_CONFIG = {
        "ip": os.getenv("CAMERA_IP", "192.168.11.34"),
        "port": int(os.getenv("CAMERA_PORT", "2020")),
        "user": os.getenv("CAMERA_USER", "admin"),
        "password": os.getenv("CAMERA_PASSWORD", ""),
    }
    GO2RTC_CAMERA_STREAM_NAME = os.getenv("GO2RTC_CAMERA_STREAM_NAME", "tapo_cam")
    DEFAULT_VOICE = "Joanna"  # Default voice when no profile is set
    logger.info("Using default camera configuration")

# Verified working RTSP streams
WORKING_STREAMS = [
    f"rtsp://{CAMERA_CONFIG['user']}:{CAMERA_CONFIG['password']}@{CAMERA_CONFIG['ip']}:554/stream1",
    f"rtsp://{CAMERA_CONFIG['user']}:{CAMERA_CONFIG['password']}@{CAMERA_CONFIG['ip']}:554/stream2",
    f"rtsp://{CAMERA_CONFIG['user']}:{CAMERA_CONFIG['password']}@{CAMERA_CONFIG['ip']}:554/stream8",
]

# go2rtc configuration
GO2RTC_API_URL = os.getenv("GO2RTC_API_URL", "http://localhost:1984/api/ffmpeg")
# GO2RTC_CAMERA_STREAM_NAME is set above based on camera profile
# Path to the audio files directory, robustly defined from this file's location
AUDIO_SAVE_DIR = project_root / "services" / "go2rtc" / "audio_files"


# Global variables
onvif_camera = None
is_initialized = False
bedrock_client = None
ptz_controller = None
tts_engine: Union[EmotionalTTS, None] = None
transcribe_client = None

# Initialize MCP app with camera profile-specific naming
mcp_name = f"Tapo Camera Control - {CAMERA_CONFIG['ip']}"
tool_prefix = ""  # No prefix by default
if CAMERA_PROFILE:
    mcp_name = f"Tapo Camera Control - {CAMERA_PROFILE.upper()}"
    tool_prefix = f"{CAMERA_PROFILE}_"  # Add prefix to tool names
    logger.info(f"Using tool prefix: '{tool_prefix}'")
mcp = FastMCP(mcp_name)


async def ensure_initialized():
    """Initialize ONVIF camera connection"""
    global onvif_camera, is_initialized, ptz_controller, tts_engine, transcribe_client

    global bedrock_client
    if not is_initialized:
        try:
            onvif_camera = ONVIFCamera(
                CAMERA_CONFIG["ip"],
                CAMERA_CONFIG["port"],
                CAMERA_CONFIG["user"],
                CAMERA_CONFIG["password"],
            )
            ptz_controller = PTZController(onvif_camera)
            await ptz_controller.connect()
            
            # Initialize AWS Bedrock client for AI analysis
            aws_region = os.getenv("AWS_REGION", "ap-northeast-1")
            logger.info(f"Initializing AWS Bedrock client in region: {aws_region}")
            bedrock_client = boto3.client(
                service_name='bedrock-runtime',
                region_name=aws_region
            )
            logger.info("AWS Bedrock client initialized successfully.")

            # Initialize TTS with AWS Polly (no credentials file needed - uses IAM/env vars)
            logger.info(f"Initializing AWS Polly TTS in region: {aws_region}")
            tts_engine = EmotionalTTS(region_name=aws_region)
            logger.info("AWS Polly TTS client initialized successfully.")

            # Initialize AWS Transcribe for STT
            logger.info(f"Initializing AWS Transcribe STT in region: {aws_region}")
            transcribe_client = AWSTranscribeClient(region_name=aws_region)
            logger.info("AWS Transcribe STT client initialized successfully.")

            is_initialized = True
            logger.info(f"ONVIF Camera initialized for {CAMERA_CONFIG['ip']}")
        except Exception as e:
            logger.error(f"Failed to initialize ONVIF camera or other clients: {e}")
            is_initialized = False


async def ensure_camera_settled():
    """Wait for camera motion to complete and stabilize."""
    # Wait briefly for camera motion to complete
    # PTZ controller's move_absolute has fixed timeout, but we add extra wait to ensure actual completion
    await asyncio.sleep(1.0)
    logger.info("Camera settling time completed.")


async def _capture_snapshot_internal() -> dict:
    """Internal helper to capture a snapshot. Returns a dict with results including base64 data."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_path = f"/tmp/tapo_snapshot_{timestamp}.jpg"
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    for i, stream_url in enumerate(WORKING_STREAMS, 1):
        try:
            logger.info(f"Attempting snapshot from stream {i}: {stream_url}")
            cmd = [
                "ffmpeg",
                "-y",
                "-rtsp_transport",
                "tcp",
                "-i",
                stream_url,
                "-frames:v",
                "1",
                "-q:v",
                "2",
                save_path,
            ]
            result = subprocess.run(
                cmd, check=False, capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0 and os.path.exists(save_path):
                file_size = os.path.getsize(save_path)
                logger.info(
                    f"Snapshot captured successfully: {save_path} ({file_size} bytes)"
                )

                # Read the image and encode it in base64
                with open(save_path, "rb") as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode("utf-8")

                # Clean up the local file immediately
                # os.remove(save_path)

                return {
                    "success": True,
                    "file_path": save_path,
                    "size": file_size,
                    "stream_index": i,
                    "stream_url": stream_url,
                    "base64_image": encoded_string,
                }
            logger.warning(f"ffmpeg failed for stream {i}: {result.stderr}")
        except subprocess.TimeoutExpired:
            logger.warning(f"Timeout for stream {i}")
        except Exception as e:
            logger.warning(f"Error with stream {i}: {e}")
    return {"success": False, "error": "All streams failed"}


async def play_audio_on_camera(audio_filename: str):
    """Play a given audio file on the camera via go2rtc API and wait for completion."""
    # File path as seen from go2rtc container (based on ./audio_files:/audio mapping in docker-compose.yml)
    audio_path_container = f"/audio/{audio_filename}"
    url = (
        f"{GO2RTC_API_URL}?dst={GO2RTC_CAMERA_STREAM_NAME}&file={audio_path_container}"
    )
    audio_path_host = AUDIO_SAVE_DIR / audio_filename

    logger.info(f"Requesting audio playback on camera via go2rtc: {url}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url) as response:
                if not 200 <= response.status < 300:
                    error_text = await response.text()
                    logger.error(
                        f"Error from go2rtc API: {response.status} - {error_text}"
                    )
                else:
                    logger.info("Audio playback request accepted by go2rtc.")

                    # Get actual audio duration using ffprobe (required for development)
                    if not audio_path_host.exists():
                        raise FileNotFoundError(
                            f"Audio file not found: {audio_path_host}"
                        )

                    try:
                        # Get actual duration using ffprobe - no fallback during development
                        result = subprocess.run(
                            [
                                "ffprobe",
                                "-v",
                                "quiet",
                                "-show_entries",
                                "format=duration",
                                "-of",
                                "csv=p=0",
                                str(audio_path_host),
                            ],
                            capture_output=True,
                            text=True,
                            timeout=5,
                        )

                        if result.returncode != 0:
                            raise RuntimeError(
                                f"ffprobe failed with return code {result.returncode}: {result.stderr}"
                            )

                        if not result.stdout.strip():
                            raise RuntimeError("ffprobe returned empty duration")

                        duration = float(result.stdout.strip())
                        logger.info(
                            f"Audio duration: {duration:.2f} seconds. Waiting for playback to complete..."
                        )
                        # Wait for the audio to finish playing, plus a small buffer
                        await asyncio.sleep(duration + 0.5)
                        logger.info("Playback finished.")

                    except (
                        subprocess.TimeoutExpired,
                        ValueError,
                        FileNotFoundError,
                    ) as e:
                        # No fallback - raise error to notice issues during development
                        raise RuntimeError(f"Failed to determine audio duration: {e}")

    except aiohttp.ClientError as e:
        logger.error(f"Failed to connect to go2rtc API: {e}")
    finally:
        # Clean up the temporary audio file after playback
        # if audio_path_host.exists():
        #     audio_path_host.unlink()
        #     logger.info(f"Cleaned up temporary audio file: {audio_path_host}")
        pass


async def _generate_tts_audio_file(text: str, voice_id: Union[str, None] = None) -> Union[str, None]:
    """Generate TTS audio using AWS Polly, convert it to WAV, and return the filename.
    
    Args:
        text: Text to synthesize
        voice_id: AWS Polly voice ID. If not specified, uses camera-specific default (Matthew for camera1, Joanna for camera2).
    """
    if not tts_engine or not tts_engine.tts.client:
        logger.warning("TTS engine not initialized.")
        return None
    
    # Use camera-specific default voice if not specified
    if voice_id is None:
        voice_id = DEFAULT_VOICE

    try:
        # Ensure the directory exists, creating parent directories if necessary
        AUDIO_SAVE_DIR.mkdir(parents=True, exist_ok=True)

        logger.info(f"Generating TTS with voice: {voice_id}")
        # Step 1: Generate MP3 from AWS Polly TTS
        temp_audio_file = await tts_engine.tts.synthesize_speech(
            text=text,
            language_code="en-US",
            voice_id=voice_id,  # AWS Polly English voice
            engine="neural",
        )

        if not temp_audio_file or not temp_audio_file.exists():
            logger.warning("TTS audio generation (MP3) failed.")
            return None

        # Step 2: Convert MP3 to WAV using ffmpeg
        output_filename = f"tts_{uuid.uuid4().hex}.wav"
        output_path = AUDIO_SAVE_DIR / output_filename
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(temp_audio_file),
            "-ar",
            "16000",  # Sample rate
            "-ac",
            "1",  # Mono channel
            str(output_path),
        ]
        result = subprocess.run(cmd, check=False, capture_output=True, text=True)

        # Clean up the original MP3 file
        temp_audio_file.unlink()

        if result.returncode != 0:
            logger.error(f"ffmpeg conversion to WAV failed: {result.stderr}")
            return None

        logger.info(f"TTS audio generated and converted to WAV: {output_path}")
        return output_filename

    except Exception as e:
        logger.error(f"Error during TTS file generation: {e}", exc_info=True)
        return None


@mcp.tool(name=f"{tool_prefix}analyze_camera_image")
async def analyze_camera_image(
    prompt: str = """
Analyze the provided image information objectively without adding your own opinions.
""",
) -> str:
    """Analyze the camera's current video feed using AI and generate a description."""
    await ensure_initialized()
    if not bedrock_client:
        return json.dumps(
            {
                "status": "error",
                "message": "AI analysis is disabled. AWS Bedrock client is not initialized.",
            }
        )

    logger.info("Starting image analysis for prompt: %s", prompt)

    # Wait for camera motion to complete and stabilize
    await ensure_camera_settled()

    snapshot_result = await _capture_snapshot_internal()
    if not snapshot_result["success"]:
        error_message = f"Image analysis failed: Could not capture image - {snapshot_result['error']}"
        return json.dumps({"status": "error", "message": error_message})

    base64_image = snapshot_result.get("base64_image")
    if not base64_image:
        return json.dumps(
            {
                "status": "error",
                "message": "Image analysis failed: No base64 image data found.",
            }
        )

    try:
        logger.info("Analyzing image with AWS Bedrock (amazon.nova-lite-v1:0)...")
        
        # Prepare the request body for AWS Bedrock Nova model
        # Note: Keep image as base64 string, not decoded bytes
        request_body = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "text": prompt
                        },
                        {
                            "image": {
                                "format": "jpeg",
                                "source": {
                                    "bytes": base64_image
                                }
                            }
                        }
                    ]
                }
            ],
            "inferenceConfig": {
                "max_new_tokens": 2048,
                "temperature": 0.7
            }
        }

        # Invoke the Bedrock model
        response = bedrock_client.invoke_model(
            modelId="amazon.nova-lite-v1:0",
            body=json.dumps(request_body)
        )

        # Parse the response
        response_body = json.loads(response['body'].read())
        analysis_text = response_body.get('output', {}).get('message', {}).get('content', [{}])[0].get('text', 'No response from AI.')
        
        logger.info("Image analysis successful.")
        logger.info("Analysis Result: %s", analysis_text)
        return json.dumps({"status": "success", "analysis": analysis_text})
    except Exception as e:
        logger.error(f"Error during AI image analysis: {e}")
        return json.dumps(
            {"status": "error", "message": f"An error occurred during AI analysis: {e}"}
        )


async def _perform_nod_head_movement():
    """Background task for the physical nod movement."""
    try:
        original_position = await ptz_controller.get_position()
        if not original_position:
            original_position = {"pan": 0.0, "tilt": 0.0, "zoom": 0.0}

        # Short wait time for quick movements
        wait_time = 1.5

        logger.info("Starting nod movement: down")
        # Nod down
        await ptz_controller.move_absolute(
            pan=original_position["pan"],
            tilt=original_position["tilt"] - 0.3,
            wait_seconds=wait_time,
        )
        logger.info("Nod down complete, moving up")
        # Nod up
        await ptz_controller.move_absolute(
            pan=original_position["pan"],
            tilt=original_position["tilt"] + 0.3,
            wait_seconds=wait_time,
        )
        logger.info("Nod up complete, returning to original position")
        # Return to original position
        await ptz_controller.move_absolute(
            pan=original_position["pan"],
            tilt=original_position["tilt"],
            wait_seconds=wait_time,
        )
        logger.info("Nod movement completed successfully.")
    except Exception as e:
        logger.error(f"Error in nod head movement: {e}")


async def _perform_shake_head_movement():
    """Background task for the physical shake movement."""
    try:
        original_position = await ptz_controller.get_position()
        if not original_position:
            original_position = {"pan": 0.0, "tilt": 0.0, "zoom": 0.0}

        # Short wait time for quick movements
        wait_time = 1.5

        logger.info("Starting shake movement: left")
        # Shake left
        await ptz_controller.move_absolute(
            pan=original_position["pan"] - 0.3,
            tilt=original_position["tilt"],
            wait_seconds=wait_time,
        )
        logger.info("Shake left complete, moving right")
        # Shake right
        await ptz_controller.move_absolute(
            pan=original_position["pan"] + 0.3,
            tilt=original_position["tilt"],
            wait_seconds=wait_time,
        )
        logger.info("Shake right complete, returning to original position")
        # Return to original position
        await ptz_controller.move_absolute(
            pan=original_position["pan"],
            tilt=original_position["tilt"],
            wait_seconds=wait_time,
        )
        logger.info("Shake movement completed successfully.")
    except Exception as e:
        logger.error(f"Error in shake head movement: {e}")


@mcp.tool(name=f"{tool_prefix}nod_head")
async def nod_head(speech_text: Union[str, None] = None, voice: Union[str, None] = None) -> str:
    """Nod the camera head up and down. Optionally, speak the given text via camera's speaker.
    
    This tool performs a complete nod animation and blocks until fully complete.
    You can optionally provide speech_text to have the camera speak while nodding.
    The camera will first generate and play the audio (if provided), then perform the nod motion.
    This tool waits for all operations to complete before returning.
    
    Args:
        speech_text: Optional text to speak via the camera's speaker during the nod. If provided, the text will be synthesized to speech and played while the camera nods.
        voice: AWS Polly voice ID. If not specified, uses camera-specific default (Matthew for camera1, Joanna for camera2). Other options: "Ivy", "Kendra", "Lotte", "Emma", "Amy", etc.
    
    Returns:
        JSON response with status and completion details. The tool BLOCKS until the nod and audio (if any) complete.
    """
    await ensure_initialized()
    if not ptz_controller or not ptz_controller.is_connected:
        return json.dumps({"status": "error", "message": "PTZ controller not ready."})

    # Use camera-specific default voice if not specified
    if voice is None:
        voice = DEFAULT_VOICE
    
    response = {
        "status": "success",
        "message": "Nod head action initiated.",
        "speech_text": None,
        "audio_file_path": None,
        "audio_base64": None,
    }

    if speech_text:
        logger.info(f"Generating audio for camera playback: '{speech_text}' with voice: {voice}")
        audio_filename = await _generate_tts_audio_file(speech_text, voice_id=voice)
        if audio_filename:
            # Play audio on the camera synchronously to prevent overlap
            await play_audio_on_camera(audio_filename)

            audio_path_host = AUDIO_SAVE_DIR / audio_filename
            # audio_base64 = ""
            # if audio_path_host.exists():
            #     with open(audio_path_host, "rb") as audio_file:
            #         audio_base64 = base64.b64encode(audio_file.read()).decode("utf-8")

            response["speech_text"] = speech_text
            response["audio_file_path"] = str(audio_path_host)
            response["audio_base64"] = ""
            response["message"] += f" Speaking: '{speech_text}'"

    # Perform the physical movement synchronously and wait for completion
    await _perform_nod_head_movement()
    logger.info("Head nod movement completed.")

    return json.dumps(response)


@mcp.tool(name=f"{tool_prefix}shake_head")
async def shake_head(speech_text: Union[str, None] = None, voice: Union[str, None] = None) -> str:
    """Shake the camera head left and right. Optionally, speak the given text via camera's speaker.
    
    This tool performs a complete shake animation and blocks until fully complete.
    You can optionally provide speech_text to have the camera speak while shaking.
    The camera will first generate and play the audio (if provided), then perform the shake motion.
    This tool waits for all operations to complete before returning.
    
    Args:
        speech_text: Optional text to speak via the camera's speaker during the shake. If provided, the text will be synthesized to speech and played while the camera shakes.
        voice: AWS Polly voice ID. If not specified, uses camera-specific default (Matthew for camera1, Joanna for camera2). Other options: "Ivy", "Kendra", "Lotte", "Emma", "Amy", etc.
    
    Returns:
        JSON response with status and completion details. The tool BLOCKS until the shake and audio (if any) complete.
    """
    await ensure_initialized()
    if not ptz_controller or not ptz_controller.is_connected:
        return json.dumps({"status": "error", "message": "PTZ controller not ready."})

    # Use camera-specific default voice if not specified
    if voice is None:
        voice = DEFAULT_VOICE
    
    response = {
        "status": "success",
        "message": "Shake head action initiated.",
        "speech_text": None,
        "audio_file_path": None,
        "audio_base64": None,
    }

    if speech_text:
        logger.info(f"Generating audio for camera playback: '{speech_text}' with voice: {voice}")
        audio_filename = await _generate_tts_audio_file(speech_text, voice_id=voice)
        if audio_filename:
            # Play audio on the camera synchronously to prevent overlap
            await play_audio_on_camera(audio_filename)

            audio_path_host = AUDIO_SAVE_DIR / audio_filename
            # audio_base64 = ""
            # if audio_path_host.exists():
            #     with open(audio_path_host, "rb") as audio_file:
            #         audio_base64 = base64.b64encode(audio_file.read()).decode("utf-8")

            response["speech_text"] = speech_text
            response["audio_file_path"] = str(audio_path_host)
            response["audio_base64"] = ""
            response["message"] += f" Speaking: '{speech_text}'"

    # Perform the physical movement synchronously and wait for completion
    await _perform_shake_head_movement()
    logger.info("Head shake movement completed.")

    return json.dumps(response)


@mcp.tool(name=f"{tool_prefix}move_camera")
async def move_camera(pan: float = 0.0, tilt: float = 0.0) -> str:
    """Move the camera by a relative amount and wait for movement to complete.
    
    This tool performs a synchronous camera movement and blocks until the movement is complete.
    The values are relative offsets from the current position, not absolute positions.
    
    Args:
        pan: Relative pan amount. Positive values move right, negative values move left. Range: -1.0 to 1.0.
        tilt: Relative tilt amount. Positive values move up, negative values move down. Range: -1.0 to 1.0.
    
    Returns:
        "OK" on success, or error message on failure. This tool BLOCKS until movement completes.
    """
    await ensure_initialized()
    if not ptz_controller or not ptz_controller.is_connected:
        return json.dumps({"status": "error", "message": "PTZ controller not ready."})

    try:
        # Get current position
        current_pos = await ptz_controller.get_position()
        if not current_pos:
            return json.dumps(
                {"status": "error", "message": "Could not get current camera position."}
            )

        # Calculate new absolute position
        new_pan = current_pos["pan"] + pan
        new_tilt = current_pos["tilt"] + tilt

        # Clamp values to be within the valid range [-1.0, 1.0]
        new_pan = max(-1.0, min(1.0, new_pan))
        new_tilt = max(-1.0, min(1.0, new_tilt))

        # Use a longer wait time for larger, synchronous movements
        success = await ptz_controller.move_absolute(
            pan=new_pan, tilt=new_tilt, wait_seconds=3.0
        )

        if success:
            return "OK"
        else:
            return "Error: Failed to move camera."
    except Exception as e:
        logger.exception("Failed to move camera")
        return json.dumps({"status": "error", "message": f"Failed to move camera: {e}"})


@mcp.tool(name=f"{tool_prefix}reset_camera_position")
async def reset_camera_position() -> str:
    """Reset the camera to its home position (pan=0, tilt=0) and wait for completion.
    
    This tool performs a synchronous camera reset to the center position and blocks until complete.
    
    Returns:
        "OK" on success, or error message on failure. This tool BLOCKS until reset completes.
    """
    await ensure_initialized()
    if not ptz_controller or not ptz_controller.is_connected:
        return json.dumps({"status": "error", "message": "PTZ controller not ready."})

    try:
        # Use a longer wait time for resetting position
        success = await ptz_controller.move_absolute(
            pan=0.0, tilt=0.0, wait_seconds=3.0
        )
        if success:
            return "OK"
        else:
            return "Error: Failed to reset camera position."
    except Exception as e:
        logger.exception("Failed to reset camera position")
        return json.dumps(
            {"status": "error", "message": f"Failed to reset camera position: {e}"}
        )


@mcp.tool(name=f"{tool_prefix}speak_on_camera")
async def speak_on_camera(speech_text: str, voice: Union[str, None] = None) -> str:
    """Output specified text as audio from the camera's speaker.
    Important: This tool blocks until audio playback is complete. Always wait for the result before proceeding to the next action.
    
    Args:
        speech_text: The text to output as audio
        voice: AWS Polly voice ID. If not specified, uses camera-specific default (Matthew for camera1, Joanna for camera2). Other options: "Ivy", "Kendra", "Lotte", "Emma", "Amy", etc.
    """
    await ensure_initialized()
    
    # Use camera-specific default voice if not specified
    if voice is None:
        voice = DEFAULT_VOICE

    if not speech_text or not speech_text.strip():
        return json.dumps(
            {
                "status": "error",
                "message": "No speech text provided.",
                "speech_text": speech_text,
            }
        )

    try:
        logger.info(f"Starting audio output on camera: '{speech_text}' with voice: {voice}")
        audio_filename = await _generate_tts_audio_file(speech_text, voice_id=voice)

        if not audio_filename:
            return json.dumps(
                {
                    "status": "error",
                    "message": "Failed to generate TTS audio file.",
                    "speech_text": speech_text,
                }
            )

        # Play audio on camera
        await play_audio_on_camera(audio_filename)

        audio_path_host = AUDIO_SAVE_DIR / audio_filename
        # audio_base64 = ""
        # if audio_path_host.exists():
        #     with open(audio_path_host, "rb") as audio_file:
        #         audio_base64 = base64.b64encode(audio_file.read()).decode("utf-8")
        # else:
        #     logger.warning(
        #         f"Audio file not found for base64 encoding: {audio_path_host}"
        #     )

        response = {
            "status": "success",
            "message": f"Audio output started successfully: '{speech_text}'",
            "speech_text": speech_text,
            "audio_file_path": str(audio_path_host),
            "audio_base64": "",
        }
        return json.dumps(response)

    except Exception as e:
        logger.error(f"Error during audio output: {e}", exc_info=True)
        return json.dumps(
            {
                "status": "error",
                "message": f"Audio output failed: {e}",
                "speech_text": speech_text,
            }
        )


@mcp.tool(name=f"{tool_prefix}listen_on_camera")
async def listen_on_camera(duration_seconds: int = 5) -> str:
    """
    Records audio from the camera for a specified duration,
    transcribes it to text using AWS Transcribe, and returns the text.
    Args:
        duration_seconds: The duration to record audio in seconds. Defaults to 10.
    """
    await ensure_initialized()
    if not transcribe_client or not transcribe_client.transcribe_client:
        return json.dumps(
            {
                "status": "error",
                "message": "AWS Transcribe client is not initialized. Check AWS credentials.",
            }
        )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_path = f"/tmp/tapo_audio_{timestamp}.wav"
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    # Use stream2 for audio recording
    stream_url = WORKING_STREAMS[1]
    logger.info(
        f"Attempting to record {duration_seconds}s of audio from stream: {stream_url}"
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-rtsp_transport",
        "tcp",
        "-i",
        stream_url,
        "-vn",  # No video
        "-acodec",
        "pcm_s16le",  # Audio codec
        "-ar",
        "8000",  # Sample rate
        "-ac",
        "1",  # Mono channel
        "-t",
        str(duration_seconds),  # Duration
        save_path,
    ]

    try:
        result = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=duration_seconds + 10,
        )

        if result.returncode != 0 or not os.path.exists(save_path):
            logger.error(f"ffmpeg audio recording failed: {result.stderr}")
            return json.dumps(
                {
                    "status": "error",
                    "message": "Failed to record audio from camera.",
                    "details": result.stderr,
                }
            )

        logger.info(f"Audio recorded successfully: {save_path}")

        # Transcribe the audio using AWS Transcribe
        logger.info("Sending audio to AWS Transcribe API...")
        transcription = await transcribe_client.transcribe_audio_file(
            audio_file_path=save_path,
            language_code="en-US",
            sample_rate=8000
        )

        if transcription:
            logger.info(f"Transcription successful: '{transcription}'")
            return json.dumps(
                {
                    "status": "success",
                    "transcription": transcription,
                }
            )
        else:
            logger.info("Transcription returned no results.")
            return json.dumps(
                {
                    "status": "success",
                    "transcription": "",
                    "message": "Audio was recorded but no speech was detected.",
                }
            )

    except subprocess.TimeoutExpired:
        logger.error("ffmpeg audio recording timed out.")
        return json.dumps(
            {
                "status": "error",
                "message": "Audio recording process timed out.",
            }
        )
    except Exception as e:
        logger.error(
            f"An unexpected error occurred during listen_on_camera: {e}", exc_info=True
        )
        return json.dumps(
            {
                "status": "error",
                "message": f"An unexpected error occurred: {e}",
            }
        )
    finally:
        # Clean up the audio file
        # if os.path.exists(save_path):
        #     os.remove(save_path)
        #     logger.info(f"Cleaned up temporary audio file: {save_path}")
        pass

if __name__ == "__main__":
    logger.info("Starting Tapo Camera Control MCP Server...")
    mcp.run()
