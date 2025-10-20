#!/usr/bin/env python3
"""AWS Text-to-Speech Integration for Tapo Camera System using Amazon Polly
AWS Polly-based speech synthesis for Tapo camera system
"""

import asyncio
import logging
import os
import tempfile
from pathlib import Path

# AWS Boto3 for Polly
try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError

    AWS_POLLY_AVAILABLE = True
except ImportError:
    AWS_POLLY_AVAILABLE = False
    logging.warning(
        "AWS Boto3 not available. Install with: pip install boto3"
    )

# Audio playback
try:
    import pygame

    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    logging.warning("Pygame not available. Install with: pip install pygame")

logger = logging.getLogger(__name__)


class AWSTextToSpeech:
    """AWS Polly Text-to-Speech wrapper for Tapo camera system"""

    def __init__(self, region_name: str = None):
        self.client = None
        self.region_name = region_name or os.getenv("AWS_REGION", "ap-northeast-1")
        self.temp_dir = Path(tempfile.gettempdir()) / "tapo_tts"
        self.temp_dir.mkdir(exist_ok=True)

        # Initialize pygame mixer for audio playback
        if PYGAME_AVAILABLE:
            try:
                # Try to initialize with specific settings for containerized environments
                pygame.mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=1024)
                pygame.mixer.init()
                logger.info("Pygame mixer initialized for audio playback")
            except Exception as e:
                try:
                    # Try with null audio driver for headless environments
                    import os
                    os.environ['SDL_AUDIODRIVER'] = 'pulse'
                    pygame.mixer.init()
                    logger.info("Pygame mixer initialized with pulse audio driver")
                except Exception as e2:
                    logger.warning(f"Audio playback not available: {e}")
                    logger.info("TTS will synthesize audio files but not play them")

        if AWS_POLLY_AVAILABLE:
            self._initialize_tts()

    def _initialize_tts(self):
        """Initialize AWS Polly client"""
        try:
            # Create Polly client with AWS credentials from environment or IAM role
            self.client = boto3.client('polly', region_name=self.region_name)
            logger.info(f"AWS Polly client initialized successfully in region: {self.region_name}")

        except Exception as e:
            logger.error(f"Failed to initialize AWS Polly: {e}")
            self.client = None

    async def synthesize_speech(
        self,
        text: str,
        language_code: str = "en-US",
        voice_id: str = "Joanna",
        engine: str = "neural",
        speed: float = 1.0,
        pitch: float = 0.0,
    ) -> Path | None:
        """Convert text to audio file
        
        Args:
            text: Text to convert to speech
            language_code: Language code (en-US, ja-JP, etc.)
            voice_id: Polly voice ID (Joanna, Matthew, etc. for English)
            engine: Voice engine ("neural" or "standard")
            speed: Speech rate (0.25 to 4.0, 1.0 = normal)
            pitch: Pitch (currently not directly supported by Polly, will use SSML workaround)
        """
        if not self.client:
            logger.error("AWS Polly client not available")
            return None

        def _synthesize():
            try:
                # Build SSML for speed control
                # Polly doesn't directly support pitch, but we can use prosody for rate
                ssml_text = f'<speak><prosody rate="{int(speed * 100)}%">{text}</prosody></speak>'
                
                # Perform synthesis
                response = self.client.synthesize_speech(
                    Engine=engine,
                    LanguageCode=language_code,
                    OutputFormat='mp3',
                    Text=ssml_text,
                    TextType='ssml',
                    VoiceId=voice_id
                )

                # Save to temporary file
                audio_file = self.temp_dir / f"tts_{hash(text) % 10000}.mp3"
                
                # Read the audio stream
                if "AudioStream" in response:
                    with open(audio_file, "wb") as out:
                        out.write(response['AudioStream'].read())
                    
                    logger.info(f"Audio content saved to {audio_file}")
                    return audio_file
                else:
                    logger.error("No AudioStream in Polly response")
                    return None

            except (BotoCoreError, ClientError) as e:
                logger.error(f"Error during AWS Polly speech synthesis: {e}")
                return None
            except Exception as e:
                logger.error(f"Unexpected error during speech synthesis: {e}")
                return None

        return await asyncio.to_thread(_synthesize)

    async def play_audio(self, audio_file: Path) -> bool:
        """Play audio file"""
        if not PYGAME_AVAILABLE:
            logger.error("Pygame not available for audio playback")
            return False

        if not audio_file.exists():
            logger.error(f"Audio file not found: {audio_file}")
            return False

        def _play():
            try:
                pygame.mixer.music.load(str(audio_file))
                pygame.mixer.music.play()

                # Wait for playback to complete
                while pygame.mixer.music.get_busy():
                    pygame.time.wait(100)

                logger.info(f"Audio playback completed: {audio_file}")
                return True

            except Exception as e:
                logger.error(f"Error during audio playback: {e}")
                return False

        return await asyncio.to_thread(_play)

    async def speak(
        self,
        text: str,
        language_code: str = "en-US",
        voice_id: str = "Joanna",
        engine: str = "neural",
        speed: float = 1.0,
        pitch: float = 0.0,
        cleanup: bool = True,
    ) -> bool:
        """Synthesize and play text as speech (one-step operation)"""
        logger.info(f"Speaking: {text}")

        # Synthesize speech
        audio_file = await self.synthesize_speech(
            text=text,
            language_code=language_code,
            voice_id=voice_id,
            engine=engine,
            speed=speed,
            pitch=pitch,
        )

        if not audio_file:
            return False

        # Play audio
        success = await self.play_audio(audio_file)

        # Cleanup temporary file
        if cleanup and audio_file.exists():
            try:
                audio_file.unlink()
                logger.debug(f"Cleaned up temporary audio file: {audio_file}")
            except Exception as e:
                logger.warning(f"Failed to cleanup audio file: {e}")

        return success

    def cleanup_temp_files(self):
        """Clean up temporary files"""
        if not self.temp_dir.exists():
            return

        try:
            for file in self.temp_dir.glob("*.mp3"):
                file.unlink()
            logger.info("Temporary audio files cleaned up")
        except Exception as e:
            logger.warning(f"Error cleaning up temporary files: {e}")

    def get_available_voices(self, language_code: str = "en-US") -> list:
        """Get list of available voices"""
        if not self.client:
            return []

        try:
            response = self.client.describe_voices(LanguageCode=language_code)
            voice_list = []
            for voice in response.get('Voices', []):
                voice_list.append(
                    {
                        "id": voice['Id'],
                        "name": voice['Name'],
                        "gender": voice.get('Gender', 'Unknown'),
                        "language_code": voice['LanguageCode'],
                        "supported_engines": voice.get('SupportedEngines', []),
                    }
                )
            return voice_list
        except Exception as e:
            logger.error(f"Error listing voices: {e}")
            return []


# Emotion-based speech configuration for AWS Polly
EMOTION_VOICE_CONFIG = {
    "happy": {"speed": 1.1, "pitch": 2.0, "voice_id": "Joanna"},
    "sad": {"speed": 0.8, "pitch": -2.0, "voice_id": "Joanna"},
    "excited": {"speed": 1.3, "pitch": 4.0, "voice_id": "Joanna"},
    "curious": {"speed": 1.0, "pitch": 1.0, "voice_id": "Joanna"},
    "thinking": {"speed": 0.9, "pitch": -1.0, "voice_id": "Joanna"},
    "surprised": {"speed": 1.2, "pitch": 3.0, "voice_id": "Joanna"},
    "neutral": {"speed": 1.0, "pitch": 0.0, "voice_id": "Joanna"},
    "confused": {"speed": 0.95, "pitch": 0.5, "voice_id": "Joanna"},
    "sleepy": {"speed": 0.7, "pitch": -3.0, "voice_id": "Joanna"},
    "alert": {"speed": 1.1, "pitch": 1.5, "voice_id": "Joanna"},
}


class EmotionalTTS:
    """Emotion-based speech synthesis (AWS Polly version)"""

    def __init__(self, region_name: str = None):
        self.tts = AWSTextToSpeech(region_name=region_name)

    async def speak_with_emotion(
        self, text: str, emotion: str = "neutral", intensity: float = 1.0
    ) -> bool:
        """Speak with emotion"""
        emotion = emotion.lower()
        config = EMOTION_VOICE_CONFIG.get(emotion, EMOTION_VOICE_CONFIG["neutral"])

        # Apply intensity scaling
        speed = config["speed"]
        pitch = config["pitch"] * intensity
        voice_id = config["voice_id"]

        return await self.tts.speak(
            text=text, voice_id=voice_id, speed=speed, pitch=pitch
        )

    async def speak_response(
        self,
        response_text: str,
        emotion: str = "neutral",
        intensity: float = 1.0,
        greeting: bool = False,
    ) -> bool:
        """Speak response with emotion"""
        # Add greeting if requested
        if greeting:
            greetings = {
                "happy": "Hello!",
                "excited": "Great!",
                "sad": "Hello...",
                "curious": "What is it?",
                "neutral": "Yes.",
            }
            greeting_text = greetings.get(emotion, "Yes.")
            full_text = f"{greeting_text} {response_text}"
        else:
            full_text = response_text

        return await self.speak_with_emotion(full_text, emotion, intensity)


# Test function
async def test_tts():
    """Test TTS functionality"""
    tts = EmotionalTTS()

    test_cases = [
        ("Hello! How are you?", "happy", 1.0),
        ("Today I feel a bit sad...", "sad", 0.8),
        ("Wow! You surprised me!", "surprised", 1.0),
        ("Well, let me think about it.", "thinking", 0.7),
    ]

    for text, emotion, intensity in test_cases:
        logger.info(f"Testing: {emotion} - {text}")
        success = await tts.speak_with_emotion(text, emotion, intensity)
        if success:
            logger.info("✅ Speech synthesis successful")
        else:
            logger.error("❌ Speech synthesis failed")
        await asyncio.sleep(1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_tts())
