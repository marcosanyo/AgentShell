#!/usr/bin/env python3
"""AWS Speech-to-Text Integration using Amazon Transcribe
Speech recognition using Amazon Transcribe
"""

import asyncio
import io
import json
import logging
import os
import time
import uuid
from pathlib import Path

# AWS Boto3 for Transcribe
try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError

    AWS_TRANSCRIBE_AVAILABLE = True
except ImportError:
    AWS_TRANSCRIBE_AVAILABLE = False
    logging.warning("AWS Boto3 not available. Install with: pip install boto3")

logger = logging.getLogger(__name__)


class AWSTranscribeClient:
    """AWS Transcribe client for speech-to-text conversion"""

    def __init__(self, region_name: str = None):
        self.region_name = region_name or os.getenv("AWS_REGION", "ap-northeast-1")
        self.transcribe_client = None
        self.s3_client = None
        self.s3_bucket = os.getenv("AWS_TRANSCRIBE_S3_BUCKET", None)

        if AWS_TRANSCRIBE_AVAILABLE:
            self._initialize_clients()

    def _initialize_clients(self):
        """Initialize AWS Transcribe and S3 clients"""
        try:
            # Create Transcribe client
            self.transcribe_client = boto3.client(
                "transcribe", region_name=self.region_name
            )

            # Create S3 client (needed for Transcribe standard API)
            # Note: Streaming API doesn't require S3
            self.s3_client = boto3.client("s3", region_name=self.region_name)

            logger.info(
                f"AWS Transcribe client initialized successfully in region: {self.region_name}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize AWS Transcribe: {e}")
            self.transcribe_client = None
            self.s3_client = None

    async def transcribe_audio_file(
        self,
        audio_file_path: str | Path,
        language_code: str = "en-US",
        sample_rate: int = 8000,
    ) -> str:
        """Transcribe audio file
        
        Args:
            audio_file_path: Path to audio file
            language_code: Language code (en-US, ja-JP, etc.)
            sample_rate: Sampling rate (Hz)
            
        Returns:
            transcription: Transcribed text
        """
        if not self.transcribe_client:
            logger.error("AWS Transcribe client not available")
            return ""

        def _transcribe():
            try:
                # Read audio file
                with open(audio_file_path, "rb") as audio_file:
                    audio_content = audio_file.read()

                # Generate unique job name
                job_name = f"transcribe-job-{uuid.uuid4().hex[:8]}-{int(time.time())}"

                # For simplicity, we'll use the streaming API approach with boto3
                # Since streaming requires different setup, we'll use a different approach
                # We'll upload to S3 if bucket is configured, otherwise use local file
                
                if self.s3_bucket:
                    # Upload to S3
                    s3_key = f"transcribe-input/{job_name}.wav"
                    self.s3_client.put_object(
                        Bucket=self.s3_bucket,
                        Key=s3_key,
                        Body=audio_content
                    )
                    media_uri = f"s3://{self.s3_bucket}/{s3_key}"
                    
                    # Start transcription job
                    self.transcribe_client.start_transcription_job(
                        TranscriptionJobName=job_name,
                        Media={'MediaFileUri': media_uri},
                        MediaFormat='wav',
                        LanguageCode=language_code,
                        Settings={
                            'ShowSpeakerLabels': False,
                        }
                    )

                    # Wait for job completion
                    max_tries = 60
                    while max_tries > 0:
                        max_tries -= 1
                        job = self.transcribe_client.get_transcription_job(
                            TranscriptionJobName=job_name
                        )
                        job_status = job['TranscriptionJob']['TranscriptionJobStatus']
                        
                        if job_status in ['COMPLETED', 'FAILED']:
                            break
                        
                        time.sleep(1)

                    if job_status == 'COMPLETED':
                        # Get transcription result
                        transcript_uri = job['TranscriptionJob']['Transcript']['TranscriptFileUri']
                        
                        # Download transcript
                        import requests
                        response = requests.get(transcript_uri)
                        transcript_data = response.json()
                        
                        # Extract transcript text
                        transcription = transcript_data['results']['transcripts'][0]['transcript']
                        
                        # Cleanup S3 object
                        try:
                            self.s3_client.delete_object(Bucket=self.s3_bucket, Key=s3_key)
                        except:
                            pass
                            
                        # Cleanup job
                        try:
                            self.transcribe_client.delete_transcription_job(
                                TranscriptionJobName=job_name
                            )
                        except:
                            pass
                        
                        logger.info(f"Transcription successful: '{transcription}'")
                        return transcription
                    else:
                        logger.error(f"Transcription job failed with status: {job_status}")
                        return ""
                else:
                    # Use streaming transcription (requires async implementation)
                    # For now, return error message
                    logger.error("S3 bucket not configured. Cannot use standard Transcribe API. Please set AWS_TRANSCRIBE_S3_BUCKET environment variable.")
                    return ""

            except (BotoCoreError, ClientError) as e:
                logger.error(f"AWS error during transcription: {e}")
                return ""
            except Exception as e:
                logger.error(f"Unexpected error during transcription: {e}")
                return ""

        return await asyncio.to_thread(_transcribe)

    async def transcribe_audio_content(
        self,
        audio_content: bytes,
        language_code: str = "en-US",
        sample_rate: int = 8000,
    ) -> str:
        """Transcribe audio data directly
        
        Args:
            audio_content: Audio data (bytes)
            language_code: Language code
            sample_rate: Sampling rate
            
        Returns:
            transcription: Transcribed text
        """
        if not self.transcribe_client:
            logger.error("AWS Transcribe client not available")
            return ""

        # Create temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            temp_file.write(audio_content)
            temp_path = temp_file.name

        try:
            result = await self.transcribe_audio_file(
                temp_path, language_code, sample_rate
            )
            return result
        finally:
            # Cleanup temp file
            try:
                os.unlink(temp_path)
            except:
                pass


# Test function
async def test_transcribe():
    """Test Transcribe functionality"""
    transcribe_client = AWSTranscribeClient()

    # This would need an actual audio file to test
    # Example usage:
    # result = await transcribe_client.transcribe_audio_file("test.wav")
    # print(f"Transcription: {result}")
    
    logger.info("AWS Transcribe client initialized")
    logger.info("To test, provide an audio file path")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_transcribe())
