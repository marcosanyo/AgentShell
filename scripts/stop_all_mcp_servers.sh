#!/bin/bash

# Stop all camera MCP servers

SCRIPT_DIR="$(dirname "$0")"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🛑 Stopping all Tapo Camera MCP Servers..."
echo "================================================="

# Function to stop a camera MCP server and all its child processes
stop_camera_server() {
    local camera_profile=$1
    local pid_file="${PROJECT_ROOT}/logs/mcp_${camera_profile}.pid"
    
    if [ -f "${pid_file}" ]; then
        local pid=$(cat "${pid_file}")
        if ps -p "${pid}" > /dev/null 2>&1; then
            echo "📹 Stopping ${camera_profile} (PID: ${pid})..."
            
            # Kill the entire process group (parent and all children)
            # Use negative PID to kill process group
            kill -TERM -"${pid}" 2>/dev/null || kill "${pid}" 2>/dev/null || true
            sleep 2
            
            # Check if still running and force kill if necessary
            if ps -p "${pid}" > /dev/null 2>&1; then
                echo "   - Force killing ${camera_profile} and its children..."
                kill -9 -"${pid}" 2>/dev/null || kill -9 "${pid}" 2>/dev/null || true
                sleep 1
            fi
            
            echo "   - ${camera_profile} stopped"
        else
            echo "📹 ${camera_profile} is not running (stale PID file)"
        fi
        rm -f "${pid_file}"
    else
        echo "📹 No PID file found for ${camera_profile}"
    fi
    
    # Additional cleanup: kill any remaining processes by port
    local port=""
    if [ "${camera_profile}" = "camera1" ]; then
        port="9006"
    elif [ "${camera_profile}" = "camera2" ]; then
        port="9007"
    fi
    
    if [ -n "${port}" ]; then
        # Find and kill processes using the port
        local port_pids=$(lsof -ti :${port} 2>/dev/null || true)
        if [ -n "${port_pids}" ]; then
            echo "   - Cleaning up processes on port ${port}..."
            echo "${port_pids}" | xargs kill -9 2>/dev/null || true
        fi
    fi
}

# Stop Camera 1
stop_camera_server "camera1"

# Stop Camera 2
stop_camera_server "camera2"

# Additional cleanup: kill any stray MCP server processes
echo ""
echo "🧹 Cleaning up any remaining MCP server processes..."
pkill -f "fastmcp run server.py" 2>/dev/null || true
pkill -f "start_mcp_server.sh" 2>/dev/null || true

echo "================================================="
echo "✅ All MCP servers stopped!"
