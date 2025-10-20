#!/bin/bash

# Start all camera MCP servers in separate terminals
# This script launches multiple MCP server instances for different cameras

set -e

SCRIPT_DIR="$(dirname "$0")"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🚀 Starting all Tapo Camera MCP Servers..."
echo "================================================="

# Check for --force or -f flag to force restart
FORCE_RESTART=false
if [ "$1" = "--force" ] || [ "$1" = "-f" ]; then
    FORCE_RESTART=true
    echo "🔄 Force restart mode enabled. Stopping existing servers first..."
    bash "${SCRIPT_DIR}/stop_all_mcp_servers.sh"
    sleep 2
fi

# Function to start a camera MCP server in background
start_camera_server() {
    local camera_profile=$1
    local log_file="${PROJECT_ROOT}/logs/mcp_${camera_profile}.log"
    local pid_file="${PROJECT_ROOT}/logs/mcp_${camera_profile}.pid"
    
    mkdir -p "${PROJECT_ROOT}/logs"
    
    # Check if already running
    if [ -f "${pid_file}" ]; then
        local old_pid=$(cat "${pid_file}")
        if ps -p "${old_pid}" > /dev/null 2>&1; then
            echo "⚠️  ${camera_profile} is already running (PID: ${old_pid})"
            echo "   Please stop it first with: bash ${SCRIPT_DIR}/stop_all_mcp_servers.sh"
            return 1
        else
            # Clean up stale PID file
            rm -f "${pid_file}"
        fi
    fi
    
    echo "📹 Starting ${camera_profile}..."
    
    # Start in background and redirect output to log file
    # Use process substitution to create a new process group
    bash -c "exec bash '${SCRIPT_DIR}/start_mcp_server.sh' '${camera_profile}'" > "${log_file}" 2>&1 &
    local pid=$!
    
    echo "   - PID: ${pid}"
    echo "   - Log: ${log_file}"
    echo "${pid}" > "${pid_file}"
    
    # Wait a moment to check if the process started successfully
    sleep 1
    if ps -p "${pid}" > /dev/null 2>&1; then
        echo "   - ✅ ${camera_profile} started successfully"
    else
        echo "   - ❌ ${camera_profile} failed to start. Check log: ${log_file}"
        rm -f "${pid_file}"
        return 1
    fi
}

# Start Camera 1
start_camera_server "camera1"
sleep 2

# Start Camera 2
start_camera_server "camera2"
sleep 2

echo "================================================="
echo "✅ All MCP servers started!"
echo ""
echo "Usage:"
echo "  To force restart:  bash ${SCRIPT_DIR}/start_all_mcp_servers.sh --force"
echo "  To stop servers:   bash ${SCRIPT_DIR}/stop_all_mcp_servers.sh"
echo ""
echo "View logs:"
echo "  tail -f ${PROJECT_ROOT}/logs/mcp_camera1.log"
echo "  tail -f ${PROJECT_ROOT}/logs/mcp_camera2.log"
echo ""
echo "Check status:"
echo "  ps aux | grep 'fastmcp run server.py'"
echo "  lsof -i :9006  # Camera 1"
echo "  lsof -i :9007  # Camera 2"
