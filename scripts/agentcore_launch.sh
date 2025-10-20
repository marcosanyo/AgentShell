#!/bin/bash
# AgentCore Runtime Launch Script for Multi-Camera Setup
# NOTE: Set these environment variables before running:
#   - CAMERA1_PASSWORD
#   - CAMERA2_PASSWORD
#   - MCP_SERVER_URLS (e.g., "https://your-ngrok-url.ngrok-free.app/sse,https://your-ngrok-url2.ngrok-free.app/sse")
#   - AGENTCORE_RUNTIME_ARN (e.g., "arn:aws:bedrock-agentcore:region:account:runtime/your-runtime")
#   - AWS_TRANSCRIBE_S3_BUCKET (optional)

if [ -z "$CAMERA1_PASSWORD" ] || [ -z "$CAMERA2_PASSWORD" ]; then
  echo "Error: CAMERA1_PASSWORD and CAMERA2_PASSWORD environment variables must be set"
  exit 1
fi

if [ -z "$MCP_SERVER_URLS" ]; then
  echo "Error: MCP_SERVER_URLS environment variable must be set"
  exit 1
fi

if [ -z "$AGENTCORE_RUNTIME_ARN" ]; then
  echo "Error: AGENTCORE_RUNTIME_ARN environment variable must be set"
  exit 1
fi

uv run agentcore launch \
  --env MCP_SERVER_URLS="$MCP_SERVER_URLS" \
  --env AWS_REGION="${AWS_REGION:-ap-northeast-1}" \
  --env BEDROCK_MODEL_ID="${BEDROCK_MODEL_ID:-apac.amazon.nova-pro-v1:0}" \
  --env AWS_TRANSCRIBE_S3_BUCKET="${AWS_TRANSCRIBE_S3_BUCKET:-agentshell-transcribe}" \
  --env AGENTCORE_RUNTIME_ARN="$AGENTCORE_RUNTIME_ARN" \
  --env CAMERA1_IP="${CAMERA1_IP:-192.168.11.34}" \
  --env CAMERA1_PORT="${CAMERA1_PORT:-2020}" \
  --env CAMERA1_USER="${CAMERA1_USER:-admin}" \
  --env CAMERA1_PASSWORD="$CAMERA1_PASSWORD" \
  --env CAMERA1_MCP_PORT="${CAMERA1_MCP_PORT:-9006}" \
  --env CAMERA1_STREAM_NAME="${CAMERA1_STREAM_NAME:-tapo_cam1}" \
  --env CAMERA2_IP="${CAMERA2_IP:-192.168.11.24}" \
  --env CAMERA2_PORT="${CAMERA2_PORT:-2020}" \
  --env CAMERA2_USER="${CAMERA2_USER:-admin}" \
  --env CAMERA2_PASSWORD="$CAMERA2_PASSWORD" \
  --env CAMERA2_MCP_PORT="${CAMERA2_MCP_PORT:-9007}" \
  --env CAMERA2_STREAM_NAME="${CAMERA2_STREAM_NAME:-tapo_cam2}"