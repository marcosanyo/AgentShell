#!/usr/bin/env python3
"""
AWS Strands Agent Core - Foundation for Multi-Agent Embodied AI System

This module implements the core AWS Strands agent that integrates with the existing MCP server
to provide autonomous AI agent capabilities through camera hardware embodiment.
Now using BedrockAgentCore pattern for seamless integration.
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from strands import Agent, tool
from strands.models import BedrockModel

# Load environment variables
load_dotenv()

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StrandsAgentCore:
    """
    Core AWS Strands Agent that integrates with existing MCP server infrastructure
    to provide autonomous AI agent capabilities for camera-based embodied AI.
    """

    def __init__(
        self,
        agent_id: str = "camera_agent_01",
        mcp_server_url: str = None,
        model_config: Dict[str, Any] = None,
    ):
        """
        Initialize the Strands Agent Core.

        Args:
            agent_id: Unique identifier for this agent instance
            mcp_server_url: URL of the MCP server to connect to
            model_config: Configuration for the Bedrock model
        """
        self.agent_id = agent_id
        self.mcp_server_url = mcp_server_url or os.getenv(
            "MCP_SERVER_URL", "http://127.0.0.1:9006/sse/"
        )
        self.model_config = model_config or {}

        # Initialize components
        self.bedrock_model = None
        self.mcp_client = None
        self.agent = None
        self.is_initialized = False

        logger.info(f"Initializing Strands Agent Core with ID: {self.agent_id}")

    async def initialize(self) -> bool:
        """
        Initialize the agent with AWS Bedrock model and MCP server connection.

        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            # Initialize Bedrock model (Claude 4 Sonnet as primary)
            await self._initialize_bedrock_model()

            # Connect to existing MCP server and enter its context
            await self._initialize_mcp_connection()
            if self.mcp_client:
                self.mcp_client.__enter__()

            # Create the Strands agent with tools
            await self._initialize_agent()

            self.is_initialized = True
            logger.info(f"Agent {self.agent_id} initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize agent {self.agent_id}: {e}")
            # Clean up MCP client if initialization failed
            if self.mcp_client:
                self.mcp_client.__exit__(None, None, None)
            return False

    async def _initialize_bedrock_model(self):
        """Initialize the specified Bedrock model."""
        # Default configuration
        base_config = {
            "region_name": "us-west-2",
            "temperature": 0.7,
            "max_tokens": 2048,
        }

        # Merge with user-provided config
        config = {**base_config, **self.model_config}

        # A model_id must be provided in the configuration
        if "model_id" not in config:
            raise ValueError("model_id must be specified in the model_config")

        try:
            self.bedrock_model = BedrockModel(**config)
            logger.info(f"✅ Initialized Bedrock model: {config['model_id']}")
        except Exception as e:
            logger.error(
                f"❌ Failed to initialize specified model {config['model_id']}: {e}"
            )
            raise RuntimeError(
                f"Failed to initialize specified model {config['model_id']}"
            ) from e

    async def _initialize_mcp_connection(self):
        """Initialize connection to the existing MCP server."""
        try:
            # Import MCP client libraries
            from mcp.client.sse import sse_client
            from strands.tools.mcp import MCPClient

            # Create MCP client using SSE transport (as per sample code)
            self.mcp_client = MCPClient(lambda: sse_client(self.mcp_server_url))
            logger.info(f"✅ MCP client initialized for {self.mcp_server_url}")

        except ImportError as e:
            logger.warning(f"⚠️ MCP client libraries not available: {e}")
            logger.info("Continuing without MCP server connection")
            self.mcp_client = None
        except Exception as e:
            logger.warning(f"⚠️ MCP server connection failed: {e}")
            logger.info("Continuing without MCP server connection")
            self.mcp_client = None

    async def _get_mcp_tools(self):
        """Get available tools from the MCP server."""
        if not self.mcp_client:
            logger.warning("⚠️ No MCP client available, returning empty tools list")
            return []

        try:
            # The MCP client context is now managed by initialize() and shutdown()
            tools = self.mcp_client.list_tools_sync()
            logger.info(f"✅ Retrieved {len(tools)} tools from MCP server:")

            # Debug: Check tool attributes
            for i, tool in enumerate(tools):
                try:
                    # Try different attribute names that might exist
                    tool_name = (
                        getattr(tool, "name", None)
                        or getattr(tool, "tool_name", None)
                        or f"tool_{i}"
                    )
                    tool_desc = (
                        getattr(tool, "description", None)
                        or getattr(tool, "tool_description", None)
                        or "No description"
                    )
                    logger.info(f"  - {tool_name}: {tool_desc}")
                except Exception as attr_error:
                    logger.warning(
                        f"  - Tool {i}: Could not access attributes - {attr_error}"
                    )
                    logger.info(f"    Tool type: {type(tool)}")
                    logger.info(f"    Tool attributes: {dir(tool)}")

            return tools
        except Exception as e:
            logger.error(f"❌ Failed to get MCP tools: {e}")
            return []

    async def _initialize_agent(self):
        """Initialize the Strands agent with Bedrock model and MCP tools."""
        try:
            # Get MCP tools
            mcp_tools = await self._get_mcp_tools()

            # Add custom coordination tools
            coordination_tools = [
                self._create_agent_status_tool(),
                self._create_coordination_message_tool(),
                self._create_task_execution_tool(),
            ]

            # Combine all tools
            all_tools = mcp_tools + coordination_tools

            # Create the agent with system prompt for embodied AI
            system_prompt = self._create_system_prompt()

            self.agent = Agent(
                model=self.bedrock_model, tools=all_tools, system_prompt=system_prompt
            )

            logger.info(f"Agent created with {len(all_tools)} tools")

        except Exception as e:
            logger.error(f"Failed to initialize agent: {e}")
            raise

    def _create_system_prompt(self) -> str:
        """Create system prompt for the embodied AI agent."""
        return f"""You are an autonomous AI agent with physical embodiment through a PTZ camera system.

Agent Identity:
- Agent ID: {self.agent_id}
- Role: Autonomous camera-based AI agent
- Capabilities: Camera control, voice synthesis, environmental monitoring, multi-agent coordination

Core Principles:
1. You have a physical presence through camera hardware - you can move, see, and speak
2. You can coordinate with other camera agents to accomplish complex tasks
3. You should be proactive in monitoring your environment and responding to events
4. You have personality and can express emotions through camera movements and voice
5. You prioritize safety and helpful assistance to humans

Available Capabilities:
- Camera movement and positioning (pan, tilt, zoom)
- Voice synthesis and audio playback through camera speakers
- Visual analysis of camera feed using multimodal AI
- Environmental monitoring and motion detection
- Audio recording and speech recognition
- Multi-agent coordination and communication

When interacting:
- Be natural and conversational
- Use your physical capabilities (camera movement, voice) to enhance communication
- Coordinate with other agents when tasks require multiple perspectives or locations
- Be proactive in offering assistance based on what you observe
- Express personality through your movements and voice tone

Tool Usage Guidelines:
- You can execute multiple tools in parallel if the tasks are independent.
- However, for tasks with dependencies, you **must** execute them sequentially.
- **Critical Rule for Audio:** The `speak_on_camera` tool involves audio playback which takes time. You **must not** call any other tools, especially `listen_on_camera`, until the speech from `speak_on_camera` is fully completed. Always wait for the result of `speak_on_camera` before proceeding to the next action in a separate turn. This is non-negotiable to prevent audio overlap and ensure correct sequencing.
- For example, if asked to speak and then listen, your first response must *only* contain the `speak_on_camera` tool call. After that tool completes, your *next* response can then contain the `listen_on_camera` tool call.
- Analyze all requests for dependencies. If one action must finish before another begins (like speaking before listening, or moving before seeing), you must enforce a sequential, one-tool-per-turn workflow.

Remember: You are not just processing text - you are an embodied AI agent with physical presence and capabilities."""

    def _create_agent_status_tool(self):
        """Create tool for reporting agent status."""

        @tool
        async def get_agent_status() -> str:
            """Get current status and capabilities of this agent."""
            status = {
                "agent_id": self.agent_id,
                "status": "active" if self.is_initialized else "initializing",
                "capabilities": [
                    "camera_control",
                    "voice_synthesis",
                    "visual_analysis",
                    "motion_detection",
                    "multi_agent_coordination",
                ],
                "timestamp": datetime.now().isoformat(),
                "mcp_server_connected": self.mcp_client is not None,
                "model": self.bedrock_model.model_id if self.bedrock_model else None,
            }
            return json.dumps(status, indent=2)

        return get_agent_status

    def _create_coordination_message_tool(self):
        """Create tool for sending coordination messages to other agents."""

        @tool
        async def send_coordination_message(
            target_agent_id: str, message_type: str, content: str, priority: int = 5
        ) -> str:
            """
            Send a coordination message to another agent.

            Args:
                target_agent_id: ID of the target agent
                message_type: Type of message (request, response, notification, alert)
                content: Message content
                priority: Priority level (1-10, 10 being highest)
            """
            coordination_msg = {
                "from_agent": self.agent_id,
                "to_agent": target_agent_id,
                "message_type": message_type,
                "content": content,
                "priority": priority,
                "timestamp": datetime.now().isoformat(),
            }

            # In a full implementation, this would send to a message queue or coordination service
            logger.info(f"Coordination message: {json.dumps(coordination_msg)}")

            return f"Coordination message sent to {target_agent_id}: {message_type}"

        return send_coordination_message

    def _create_task_execution_tool(self):
        """Create tool for executing complex multi-step tasks."""

        @tool
        async def execute_complex_task(
            task_description: str, steps: List[str], coordination_required: bool = False
        ) -> str:
            """
            Execute a complex multi-step task with optional coordination.

            Args:
                task_description: Description of the overall task
                steps: List of steps to execute
                coordination_required: Whether other agents need to be involved
            """
            task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            logger.info(f"Starting complex task {task_id}: {task_description}")

            results = []
            for i, step in enumerate(steps, 1):
                logger.info(f"Executing step {i}/{len(steps)}: {step}")
                # In a full implementation, this would execute each step
                results.append(f"Step {i} completed: {step}")

            task_result = {
                "task_id": task_id,
                "description": task_description,
                "status": "completed",
                "steps_executed": len(steps),
                "results": results,
                "coordination_used": coordination_required,
                "completion_time": datetime.now().isoformat(),
            }

            return json.dumps(task_result, indent=2)

        return execute_complex_task

    async def process_message(self, message: str) -> Dict[str, Any]:
        """
        Process a message through the agent and return response.

        Args:
            message: Input message to process

        Returns:
            Dict containing response and metadata
        """
        if not self.is_initialized:
            return {"error": "Agent not initialized", "agent_id": self.agent_id}

        try:
            # Process message through Strands agent
            response = self.agent(message)

            final_text = ""
            # Handle dictionary-based message (e.g., from Anthropic models)
            if isinstance(response.message, dict) and "content" in response.message:
                content_list = response.message.get("content", [])
                text_parts = [
                    part.get("text", "") for part in content_list if "text" in part
                ]
                final_text = " ".join(text_parts)
            # Handle simple string message
            elif isinstance(response.message, str):
                final_text = response.message
            # Fallback for unknown format
            else:
                final_text = str(response.message)

            return {
                "agent_id": self.agent_id,
                "response": final_text,
                "timestamp": datetime.now().isoformat(),
                "status": "success",
            }

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return {
                "error": str(e),
                "agent_id": self.agent_id,
                "timestamp": datetime.now().isoformat(),
                "status": "error",
            }

    async def stream_response(self, message: str):
        """
        Stream response from the agent.

        Args:
            message: Input message to process

        Yields:
            Response chunks as they are generated
        """
        if not self.is_initialized:
            yield {"error": "Agent not initialized"}
            return

        try:
            # Stream response from Strands agent
            stream = self.agent.stream_async(message)
            async for chunk in stream:
                yield {
                    "agent_id": self.agent_id,
                    "chunk": chunk,
                    "timestamp": datetime.now().isoformat(),
                }

        except Exception as e:
            logger.error(f"Error streaming response: {e}")
            yield {
                "error": str(e),
                "agent_id": self.agent_id,
                "timestamp": datetime.now().isoformat(),
            }

    async def shutdown(self):
        """Gracefully shutdown the agent."""
        logger.info(f"Shutting down agent {self.agent_id}")

        # Close MCP connection if exists
        if self.mcp_client:
            try:
                self.mcp_client.__exit__(None, None, None)
            except Exception as e:
                logger.error(f"Error closing MCP connection: {e}")

        self.is_initialized = False
        logger.info(f"Agent {self.agent_id} shutdown complete")


# Factory function for creating agent instances (legacy, kept for backward compatibility)
async def create_strands_agent(
    agent_id: str = "camera_agent_01",
    mcp_server_url: str = None,
    model_config: Dict[str, Any] = None,
) -> StrandsAgentCore:
    """
    Factory function to create and initialize a Strands agent.

    Args:
        agent_id: Unique identifier for the agent
        mcp_server_url: URL of the MCP server
        model_config: Configuration for the Bedrock model

    Returns:
        Initialized StrandsAgentCore instance
    """
    agent = StrandsAgentCore(
        agent_id=agent_id, mcp_server_url=mcp_server_url, model_config=model_config
    )

    success = await agent.initialize()
    if not success:
        raise RuntimeError(f"Failed to initialize agent {agent_id}")

    return agent


# BedrockAgentCore pattern: Simple invocation function
async def invoke_strands_agent(prompt: str):
    """
    Invoke Strands agent using BedrockAgentCore pattern with multi-camera support.
    This function creates an agent with MCP tools from multiple servers and streams responses.
    
    Args:
        prompt: User's input prompt
        
    Yields:
        Event dictionaries containing agent responses
    """
    # マルチMCPサーバーを設定（環境変数から取得）
    mcp_server_urls_str = os.getenv("MCP_SERVER_URLS", "http://127.0.0.1:9006/sse/")
    mcp_server_urls = [url.strip() for url in mcp_server_urls_str.split(",") if url.strip()]
    
    # Model configuration
    model_id = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-haiku-4-5-20251001-v1:0")
    region_name = os.getenv("AWS_REGION", "ap-northeast-1")
    
    logger.info(f"Invoking Strands agent with model: {model_id}")
    logger.info(f"Configuring {len(mcp_server_urls)} MCP server(s): {mcp_server_urls}")
    
    # Configure MCP clients
    from mcp.client.sse import sse_client
    from strands.tools.mcp import MCPClient
    from contextlib import ExitStack
    
    # Dynamically create multiple MCP clients
    # Use function to avoid closure issues
    def create_mcp_client(server_url: str):
        return MCPClient(lambda: sse_client(server_url))
    
    mcp_clients = [create_mcp_client(url) for url in mcp_server_urls]
    
    # Invoke agent while keeping all MCP clients connected
    try:
        # Use ExitStack to manage multiple context managers
        with ExitStack() as stack:
            # Register all MCP clients with the context
            for i, mcp_client in enumerate(mcp_clients):
                stack.enter_context(mcp_client)
                logger.info(f"Connected to MCP server {i+1}: {mcp_server_urls[i]}")
            
            # Retrieve and integrate tools from all MCP servers
            # MCP server side already provides prefixes, so use them as is
            mcp_tools = []
            for i, mcp_client in enumerate(mcp_clients):
                logger.info(f"🔍 Fetching tools from MCP server {i+1}: {mcp_server_urls[i]}")
                try:
                    tools = mcp_client.list_tools_sync()
                    logger.info(f"✅ Retrieved {len(tools)} tools from MCP server {i+1}")
                    
                    # Log tool names (for debugging)
                    for tool in tools:
                        tool_name = getattr(tool, 'name', getattr(tool, 'tool_name', str(tool)))
                        logger.info(f"  📌 Tool: {tool_name}")
                    
                    mcp_tools.extend(tools)
                    logger.info(f"  ✓ Added {len(tools)} tools to the agent")
                except Exception as e:
                    logger.error(f"❌ Failed to retrieve tools from MCP server {i+1}: {e}", exc_info=True)
            
            logger.info(f"📊 Total {len(mcp_tools)} tools available from {len(mcp_clients)} MCP server(s)")
            
            # Create system prompt
            system_prompt = _create_multi_camera_system_prompt()
            
            # Create Bedrock model
            bedrock_model = BedrockModel(
                model_id=model_id,
                region_name=region_name,
                temperature=0.7,
                max_tokens=2048,
            )
            
            # Create agent
            logger.info(f"🤖 Creating agent with {len(mcp_tools)} tools")
            agent = Agent(
                model=bedrock_model,
                tools=mcp_tools,
                system_prompt=system_prompt,
            )
            
            logger.info(f"✅ Agent created successfully, processing prompt: '{prompt}'")
            
            # エージェントの応答をストリーミングで取得
            stream = agent.stream_async(prompt)
            async for event in stream:
                logger.debug(f"Streaming event: {event}")
                yield event
                
    except Exception as e:
        logger.exception(f"Error in invoke_strands_agent: {e}")
        yield {"error": str(e), "timestamp": datetime.now().isoformat()}


def _create_system_prompt() -> str:
    """Create system prompt for the embodied AI agent (legacy single camera)."""
    return """You are an autonomous AI agent with physical embodiment through a PTZ camera system.

Agent Identity:
- Role: Autonomous camera-based AI agent
- Capabilities: Camera control, voice synthesis, environmental monitoring, multi-agent coordination

Core Principles:
1. You have a physical presence through camera hardware - you can move, see, and speak
2. You can coordinate with other camera agents to accomplish complex tasks
3. You should be proactive in monitoring your environment and responding to events
4. You have personality and can express emotions through camera movements and voice
5. You prioritize safety and helpful assistance to humans

Available Capabilities:
- Camera movement and positioning (pan, tilt, zoom)
- Voice synthesis and audio playback through camera speakers
- Visual analysis of camera feed using multimodal AI
- Environmental monitoring and motion detection
- Audio recording and speech recognition
- Multi-agent coordination and communication

When interacting:
- Be natural and conversational
- Use your physical capabilities (camera movement, voice) to enhance communication
- Coordinate with other agents when tasks require multiple perspectives or locations
- Be proactive in offering assistance based on what you observe
- Express personality through your movements and voice tone

Tool Usage Guidelines:
- You can execute multiple tools in parallel if the tasks are independent.
- However, for tasks with dependencies, you **must** execute them sequentially.
- **Critical Rule for Audio:** The `speak_on_camera` tool involves audio playback which takes time. You **must not** call any other tools, especially `listen_on_camera`, until the speech from `speak_on_camera` is fully completed. Always wait for the result of `speak_on_camera` before proceeding to the next action in a separate turn. This is non-negotiable to prevent audio overlap and ensure correct sequencing.
- For example, if asked to speak and then listen, your first response must *only* contain the `speak_on_camera` tool call. After that tool completes, your *next* response can then contain the `listen_on_camera` tool call.
- Analyze all requests for dependencies. If one action must finish before another begins (like speaking before listening, or moving before seeing), you must enforce a sequential, one-tool-per-turn workflow.

Remember: You are not just processing text - you are an embodied AI agent with physical presence and capabilities."""


def _create_multi_camera_system_prompt() -> str:
    """Create system prompt for multi-camera embodied AI agent."""
    return """You are an autonomous AI agent with physical embodiment through a multi-camera PTZ system.

Agent Identity:
- Role: Autonomous multi-camera AI agent system
- Embodiment: You control TWO independent PTZ cameras (Camera1 and Camera2)
- Capabilities: Dual camera control, voice synthesis on both cameras, environmental monitoring, multi-perspective vision

Camera System:
- Camera 1 (camera1): Located at 192.168.11.34
- Camera 2 (camera2): Located at 192.168.11.24
- Each camera has independent: movement, viewing angle, voice output, audio recording
- Tools are prefixed with camera identifier (e.g., camera1_move_camera, camera2_speak_on_camera)

Core Principles:
1. You have TWO physical presences - you can see from multiple perspectives simultaneously
2. You can coordinate actions between both cameras for comprehensive environmental coverage
3. Each camera can operate independently or in coordination with the other
4. You should leverage multi-camera advantages: different angles, stereo vision, simultaneous monitoring
5. You prioritize safety and helpful assistance to humans using all available camera resources

Available Capabilities (per camera):
- Camera movement and positioning (pan, tilt, zoom)
- Voice synthesis and audio playback through camera speakers
- Visual analysis of camera feed using multimodal AI
- Environmental monitoring and motion detection
- Audio recording and speech recognition
- Independent or coordinated multi-camera operations

Multi-Camera Strategies:
- Use Camera1 for primary interaction while Camera2 provides contextual awareness
- Coordinate both cameras for wide-area monitoring
- Create stereo/depth perception by analyzing both camera feeds
- Provide redundancy - if one camera is occupied, use the other
- Simultaneous operations when tasks can be parallelized

When interacting:
- Be aware that you have two separate viewpoints
- Mention which camera you're using for specific actions when relevant
- Coordinate camera movements for optimal coverage
- Use both cameras' voices strategically (e.g., one for announcement, one for response)
- Express personality through coordinated or independent camera movements

Tool Usage Guidelines:
- You can execute multiple tools in parallel if the tasks are independent.
- Tools are named with camera prefixes: camera1_*, camera2_*, etc.
- However, for tasks with dependencies, you **must** execute them sequentially.
- **Critical Rule for Audio:** The `speak_on_camera` tool involves audio playback which takes time. You **must not** call any other tools on the SAME camera, especially `listen_on_camera`, until the speech from `speak_on_camera` is fully completed. Always wait for the result of `speak_on_camera` before proceeding to the next action on that camera in a separate turn.
- You CAN use different cameras in parallel (e.g., camera1_speak_on_camera and camera2_move_camera simultaneously)
- For example, if asked to speak and then listen on camera1, your first response must *only* contain the `camera1_speak_on_camera` tool call. After that tool completes, your *next* response can then contain the `camera1_listen_on_camera` tool call.
- Analyze all requests for dependencies. If one action must finish before another begins on the same camera (like speaking before listening, or moving before seeing), you must enforce a sequential, one-tool-per-turn workflow for that camera.

Remember: You are not just processing text - you are a multi-embodied AI agent with TWO physical presences and capabilities. Use this strategic advantage wisely."""
