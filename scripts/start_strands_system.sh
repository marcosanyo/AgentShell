#!/bin/bash

# Start AWS Strands Multi-Agent Embodied AI System
# This script starts both the MCP server and the Strands agent server

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if a port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to wait for service to be ready
wait_for_service() {
    local url=$1
    local service_name=$2
    local max_attempts=30
    local attempt=1
    
    print_status "Waiting for $service_name to be ready..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s "$url" >/dev/null 2>&1; then
            print_success "$service_name is ready!"
            return 0
        fi
        
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    print_error "$service_name failed to start within expected time"
    return 1
}

# Function to cleanup background processes
cleanup() {
    print_status "Shutting down services..."
    
    if [ ! -z "$MCP_PID" ]; then
        print_status "Stopping MCP server (PID: $MCP_PID)"
        kill $MCP_PID 2>/dev/null || true
    fi
    
    if [ ! -z "$STRANDS_PID" ]; then
        print_status "Stopping Strands agent server (PID: $STRANDS_PID)"
        kill $STRANDS_PID 2>/dev/null || true
    fi
    
    # Wait a moment for graceful shutdown
    sleep 2
    
    # Force kill if still running
    if [ ! -z "$MCP_PID" ] && kill -0 $MCP_PID 2>/dev/null; then
        print_warning "Force killing MCP server"
        kill -9 $MCP_PID 2>/dev/null || true
    fi
    
    if [ ! -z "$STRANDS_PID" ] && kill -0 $STRANDS_PID 2>/dev/null; then
        print_warning "Force killing Strands agent server"
        kill -9 $STRANDS_PID 2>/dev/null || true
    fi
    
    print_success "Cleanup complete"
}

# Set up signal handlers
trap cleanup EXIT INT TERM

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

print_status "Starting AWS Strands Multi-Agent Embodied AI System"
print_status "Project root: $PROJECT_ROOT"

# Change to project root
cd "$PROJECT_ROOT"

# Check if uv is available
if ! command -v uv &> /dev/null; then
    print_error "uv is not installed. Please install uv first:"
    print_error "curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

print_status "Using uv for dependency management and execution"

# Check environment variables
if [ -f ".env" ]; then
    print_status "Loading environment variables from .env"
    export $(grep -v '^#' .env | xargs)
else
    print_warning "No .env file found. Using default configuration."
fi

# Set default ports
MCP_PORT=${MCP_PORT:-9006}
STRANDS_PORT=${STRANDS_SERVER_PORT:-8001}

print_status "Configuration:"
print_status "  MCP Server Port: $MCP_PORT"
print_status "  Strands Agent Server Port: $STRANDS_PORT"
print_status "  MCP Server URL: ${MCP_SERVER_URL:-http://127.0.0.1:$MCP_PORT/sse/}"

# Check if ports are already in use
if check_port $MCP_PORT; then
    print_error "Port $MCP_PORT is already in use. Please stop the service using this port or change MCP_PORT."
    exit 1
fi

if check_port $STRANDS_PORT; then
    print_error "Port $STRANDS_PORT is already in use. Please stop the service using this port or change STRANDS_SERVER_PORT."
    exit 1
fi

# Start MCP Server
print_status "Starting MCP Server on port $MCP_PORT..."
uv run python mcp_server/server.py &
MCP_PID=$!

print_status "MCP Server started with PID: $MCP_PID"

# Wait for MCP server to be ready
if ! wait_for_service "http://127.0.0.1:$MCP_PORT/health" "MCP Server"; then
    print_error "MCP Server failed to start"
    exit 1
fi

# Start Strands Agent Server
print_status "Starting Strands Agent Server on port $STRANDS_PORT..."
uv run python strands_agent/server.py &
STRANDS_PID=$!

print_status "Strands Agent Server started with PID: $STRANDS_PID"

# Wait for Strands server to be ready
if ! wait_for_service "http://127.0.0.1:$STRANDS_PORT/health" "Strands Agent Server"; then
    print_error "Strands Agent Server failed to start"
    exit 1
fi

print_success "🎉 AWS Strands Multi-Agent Embodied AI System is running!"
print_status ""
print_status "Services:"
print_status "  📹 MCP Server (Camera Control): http://127.0.0.1:$MCP_PORT"
print_status "  🤖 Strands Agent Server: http://127.0.0.1:$STRANDS_PORT"
print_status ""
print_status "API Documentation:"
print_status "  📚 Strands Agent API: http://127.0.0.1:$STRANDS_PORT/docs"
print_status ""
print_status "Quick Test Commands:"
print_status "  curl http://127.0.0.1:$STRANDS_PORT/health"
print_status "  curl http://127.0.0.1:$STRANDS_PORT/agents"
print_status ""
print_status "To test the integration:"
print_status "  uv run python strands_agent/test_integration.py"
print_status ""
print_status "Press Ctrl+C to stop all services"

# Keep the script running and monitor the processes
while true; do
    # Check if MCP server is still running
    if ! kill -0 $MCP_PID 2>/dev/null; then
        print_error "MCP Server (PID: $MCP_PID) has stopped unexpectedly"
        break
    fi
    
    # Check if Strands server is still running
    if ! kill -0 $STRANDS_PID 2>/dev/null; then
        print_error "Strands Agent Server (PID: $STRANDS_PID) has stopped unexpectedly"
        break
    fi
    
    sleep 5
done

print_error "One or more services have stopped. Shutting down..."
exit 1