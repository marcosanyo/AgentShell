# AgentShell: From Model Context to Control
**Redefining MCP from Data Access to Physical Body Control**

AgentShell enables cloud-based AI to **possess physical PTZ cameras** as embodied agents, transforming how AI interacts with the physical world. Instead of constant surveillance, AI **appears when called**—seeing, speaking, and acting through autonomous camera control.

**Core Innovation**: We've redefined the **Model Context Protocol (MCP) from "information retrieval" to "body control,"** giving AI physical presence through vision, voice, and movement.

## 🎯 The Concept

**One Mind, Many Bodies**

A single cloud AI consciousness (Amazon Bedrock AgentCore + Strands Agents) controls multiple physical "bodies" (PTZ cameras) through the Model Context Protocol—redefined from "information retrieval" to "body control."

### Key Innovation: MCP as a Body Interface

We've transformed MCP from a **data access protocol** into a **physical control interface**, giving AI:
- 👁️ **Vision**: Snapshot capture & multimodal analysis (Amazon Bedrock Nova)
- 🎙️ **Voice**: Natural speech synthesis & recognition (AWS Polly/Transcribe)
- 🤖 **Movement**: PTZ control, nods, shakes for emotional expression (ONVIF)
- 🧠 **Autonomy**: Self-selects cameras and tools via agentic loop (Strands Agents)
- 🔒 **Security**: Secure remote control without exposing camera ports
- 📈 **Scalability**: Horizontal scaling by simply adding MCP servers

**Key Paradigm**: A single cloud consciousness inhabits multiple camera bodies only when needed, executing **see → think → speak → listen** cycles autonomously.

### 💰 Extreme Cost-Effectiveness

**Transform affordable surveillance cameras into AI agents**

AgentShell brings enterprise-grade AI capabilities to **consumer-level PTZ cameras**:

- 💵 **Hardware**: ~$20-40 per camera (Tapo C210, similar ONVIF cameras)
- 🤖 **AI Power**: Full agentic capabilities via cloud (Bedrock AgentCore + Strands)
- 🔄 **Reuse existing equipment**: No need for specialized expensive hardware
- 📊 **Pay-per-use**: AWS charges only when agent is active (not 24/7 surveillance)
- 🌐 **Scale economically**: Each additional camera costs only ~$20-40

**Cost comparison**:
- Traditional AI camera systems: **$500-2000+ per camera** (dedicated hardware)
- AgentShell approach: **$20-40 camera + cloud compute** (only when active)
- **Up to 50x cost reduction** while gaining more flexibility and intelligence

**Real-world example**:
- 5-camera home setup: ~$100-200 (cameras) vs $2,500-10,000 (traditional AI cameras)
- Business deployment: 20 cameras for ~$400-800 vs $10,000-40,000
- **No maintenance costs** for on-premise AI servers
- **Automatic updates** through cloud AI improvements

**Democratization**: Makes AI agent technology accessible to homes, small businesses, and developing regions.

## ✨ What Makes This Special

### 1. **MCP Paradigm Shift**
First project to demonstrate MCP as a **"body interface"** rather than just data access. Traditional MCP enables AI to access **data and context**. We repurposed it for **physical control**—proving AI can control physical devices through standard protocols.

### 2. **Embodied AI with Agentic Loop**
True **"One Mind, Many Bodies"** implementation:
- Single consciousness inhabits multiple physical forms
- Autonomous camera and tool selection (no manual routing)
- Seamless possession transitions between bodies
- Strands Agents' **agentic loop** orchestrates MCP tool calls autonomously

### 3. **Physical Body Language**
PTZ camera movements create **emotional presence** and natural interaction:
- **Nods** for agreement
- **Head shakes** for negation
- **Gaze shifts** to look around
- **Multiple voices** for character expression (AWS Polly: Matthew, Joanna, etc.)
- Visual + audio feedback builds trust

### 4. **On-Demand Intervention Model**
New paradigm: **Not constant surveillance, but appears when called**
- Balances privacy and peace of mind
- Cost-efficient (cloud compute only when active)
- Trust-building experience

### 5. **Security by Design**
- ✅ **No camera port exposure** (RTSP/management API remain local)
- ✅ All control flows through **authorized remote MCP**
- ✅ **One-way tunnel** connection via ngrok/cloudflared
- ✅ Centralized operations and auditing

### 6. **Effortless Scaling**
**Adding MCP = Adding a body**. No UI or workflow changes required.
- Same agent, same policy, infinite cameras
- Theoretically unlimited expansion

### 7. **Cost Democratization**
Enterprise AI capabilities with **consumer-grade hardware** (~$20-40/camera vs $500-2000+ for traditional AI cameras). **Up to 50x cost reduction** while maintaining full agentic intelligence. Transforms expensive technology into accessible solutions for everyone.

## 🎬 Demo Scenario: Visitor Response

### 📹 Demo Video

Watch AgentShell in action:

[![AgentShell Demo](https://img.youtube.com/vi/Wt0n9WLfi5o/0.jpg)](https://youtu.be/Wt0n9WLfi5o)

**Situation**: Visitor at the front door. Two cameras: living room + entrance.

1. **🔔 Doorbell rings**
2. **🎙️ "Alexa, start Agent Shell"** (via Alexa Developer Console)
3. **🤖 Living room camera**: "Hello! I'm Agent Shell. How can I assist you?"
4. **👤 You**: "Please ask the visitor at the front door what they need."
5. **👁️ *Possession effect: Living → Door***
6. **🚪 Front door camera**: "Hello at the door—how may I help you today?"
7. **📦 Visitor**: "I have a delivery for Mr. Kanamaru."
8. **👁️ *Possession effect: Door → Living***
9. **📢 Living room camera**: "The visitor says they have a delivery for Ryota Kanamaru."
10. **👤 You**: "Please tell them to leave it at the door."
11. **👁️ *Possession effect: Living → Door***
12. **🚪 Front door camera**: "Please leave the package at the door. Thank you."

> **Continuous interaction**: After each report, the agent automatically listens for your next instruction via `listen_on_camera`, creating a natural conversation flow.

---

**Additional demo**: [Camera movement demonstration](https://youtu.be/DyWGClwT0DE)

## 🏗️ Architecture & Tech Stack

![AgentShell Architecture](docs/agentshell_architecture.png)

### System Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Cloud Layer (AWS)                                      │
│  • Amazon Bedrock AgentCore (Agentic Loop)             │
│  • Strands Agents SDK (MCP Tool Orchestration)         │
│  • Amazon Bedrock Nova (Multimodal Image Analysis)     │
│  • AWS Polly/Transcribe (Voice I/O)                    │
│  • Amazon S3 (Snapshot Storage)                        │
└────────────────────┬────────────────────────────────────┘
                     │ Authorized Remote MCP
                     │ (ngrok/cloudflared tunnel)
┌────────────────────┴────────────────────────────────────┐
│  Local MCP Servers (FastMCP Framework)                 │
│  • camera1_* tools (7 tools per camera)                │
│  • camera2_* tools                                     │
│    - analyze_camera_image, speak_on_camera             │
│    - listen_on_camera, move_camera                     │
│    - nod_head, shake_head, reset_position             │
│  • go2rtc (RTSP Stream & Audio Management)             │
└────────────────────┬────────────────────────────────────┘
                     │ ONVIF/RTSP (Local Network Only)
┌────────────────────┴────────────────────────────────────┐
│  Physical Devices                                       │
│  • PTZ Cameras × 2                                     │
└─────────────────────────────────────────────────────────┘
```

### Security Architecture

**Traditional approach (❌ Not secure)**:
```
Cloud AI → Direct RTSP/API → Camera (ports exposed to internet)
```

**Our approach (✅ Secure)**:
```
Cloud AI → Authorized MCP → ngrok tunnel → Local MCP Server → Camera (no port exposure)
```

**Security Features**:
- ✅ **No camera port exposure** (RTSP/management API remain local)
- ✅ **One-way tunnel** connection via ngrok/cloudflared
- ✅ **Authorized MCP only** - all control flows through authenticated endpoints

> **Note**: Currently in experimental phase. Authorization mechanisms are planned for production deployment.

## 🚀 Quick Start

### Prerequisites

- **Python**: 3.11+ (3.13 recommended)
- **uv**: Python package manager
- **AWS Account**: Bedrock access with Nova model
- **PTZ Camera**: Tapo C210 (~$20-40) or any ONVIF-compatible camera
  - **Cost advantage**: Use affordable consumer cameras instead of expensive AI cameras ($500-2000+)
  - **No specialized hardware needed**: Standard surveillance cameras work perfectly
- **ngrok** or **cloudflared**: For secure tunneling (free tier available)

### 1. Installation

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync
```

### 2. Environment Configuration

Create `.env` file in project root:

#### Multi-Camera Setup (Recommended)

```bash
# AWS Configuration
AWS_REGION=ap-northeast-1
BEDROCK_MODEL_ID=apac.amazon.nova-pro-v1:0

# MCP Servers (comma-separated for multiple cameras)
MCP_SERVER_URLS=http://127.0.0.1:9006/sse/,http://127.0.0.1:9007/sse/

# Camera 1 (Living Room)
CAMERA1_IP=192.168.11.34
CAMERA1_PORT=2020
CAMERA1_USER=your_username
CAMERA1_PASSWORD=your_password
CAMERA1_STREAM_NAME=tapo_cam1

# Camera 2 (Front Door)
CAMERA2_IP=192.168.11.24
CAMERA2_PORT=2020
CAMERA2_USER=your_username
CAMERA2_PASSWORD=your_password
CAMERA2_STREAM_NAME=tapo_cam2

# go2rtc Configuration
GO2RTC_API_URL=http://localhost:1984/api/ffmpeg
```

#### Single Camera Setup

```bash
# AWS Configuration
AWS_REGION=ap-northeast-1
BEDROCK_MODEL_ID=apac.amazon.nova-pro-v1:0

# MCP Server (single URL)
MCP_SERVER_URL=http://127.0.0.1:9006/sse/

# Camera Configuration
CAMERA_IP=192.168.11.34
CAMERA_PORT=2020
CAMERA_USER=your_username
CAMERA_PASSWORD=your_password
GO2RTC_CAMERA_STREAM_NAME=tapo_cam
```

### 3. AWS Setup

```bash
# Configure AWS credentials
aws configure

# Request Bedrock model access
# Go to AWS Console → Amazon Bedrock → Model access
# Request access to:
# - Amazon Nova Pro/Micro
# - Anthropic Claude 3.5/4 Sonnet (optional)
```

### 4. Start Services

#### Multi-Camera Setup

```bash
# Terminal 1: Start all MCP servers
bash scripts/start_all_mcp_servers.sh

# Terminal 2: Start AgentCore (local testing)
bash scripts/start_agentcore.sh

# Terminal 3: Test the system
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Please ask the visitor at the front door what they need"}'
```

#### Single Camera Setup

```bash
# Terminal 1: Start MCP server
bash scripts/start_mcp_server.sh

# Terminal 2: Start AgentCore
bash scripts/start_agentcore.sh

# Terminal 3: Test
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Look around and tell me what you see"}'
```

### 5. Deploy to AWS (Production)

```bash
# Publish MCP server via ngrok
ngrok http 9006  # Note the public URL

# Deploy AgentCore to AWS
uv run agentcore launch \
  --env MCP_SERVER_URLS="https://your-ngrok-url/sse/" \
  --env AWS_REGION="ap-northeast-1" \
  --env BEDROCK_MODEL_ID="apac.amazon.nova-pro-v1:0"

# Check deployment status
uv run agentcore status

# Test deployed agent
uv run agentcore invoke '{"prompt": "Hello, can you hear me?"}'
```

## 🛠️ Available MCP Tools (Per Camera)

Each MCP server provides 7 tools with camera-specific prefixes (`camera1_`, `camera2_`):

### Core Tools

| Tool | Description | Example |
|------|-------------|---------|
| `analyze_camera_image` | Analyze camera view using AI (Nova) | Identify objects, people, situations |
| `speak_on_camera` | Output speech via camera speaker | Greet visitors, provide information |
| `listen_on_camera` | Record and transcribe audio | Listen to user commands, visitor responses |
| `move_camera` | Pan/tilt camera control | Look around, track movement |
| `nod_head` | Nod camera up/down (with optional speech) | Show agreement, acknowledgment |
| `shake_head` | Shake camera left/right (with optional speech) | Show disagreement, negation |
| `reset_camera_position` | Return camera to home position | Reset to default view |

### Voice Configuration

- **Camera 1** (Living room): Default voice = **Matthew** (male)
- **Camera 2** (Front door): Default voice = **Joanna** (female)
- Other available voices: Ivy, Kendra, Emma, Amy, Justin, Joey, Salli, etc.

Example:
```json
{
  "prompt": "camera1_nod_head(speech_text='I understand', voice='Matthew')"
}
```

## 📡 System Behavior

### Strict Execution Rules (Defined in System Prompt)

1. **No Parallel Calls on Same Camera**: Each camera executes ONE tool at a time
2. **Cross-Camera Parallelism Allowed**: Different cameras can operate simultaneously
3. **Sequential Pattern**: Multi-step tasks execute one tool per response
4. **Synchronous Operations**: All tools block until completion
5. **Preferred Communication**: Use `nod_head` with `speech_text` for natural interaction

### Example Workflow

**User**: "Please ask the visitor at the front door what they need."

**Agent Execution**:
1. `camera1_nod_head(speech_text="I understand. Let me check the front door for you.")`
2. `camera2_nod_head(speech_text="Hello at the door, how may I help you today?")`
3. `camera2_listen_on_camera(duration_seconds=5)`
4. `camera2_analyze_camera_image(prompt="Describe the person briefly")`
5. `camera1_nod_head(speech_text="The visitor says [message]. They appear to be [description].")`
6. `camera1_listen_on_camera(duration_seconds=10)` ← **Continues listening for next instruction**

## 🎯 Use Cases

### 🍼 Baby/Elderly Care
- **Privacy-focused**: On-demand intervention, not constant surveillance
- **Voice interaction**: Soothe baby, remind elderly of medication
- **Visual check**: Assess situation through AI analysis
- **Peace of mind**: Balances safety and privacy

### ♿ Visual Impairment Support
- **Surrogate eyes**: AI becomes your eyes, delivers info via voice
- **Product information**: "What's the expiration date?" → Camera reads label
- **Navigation assistance**: Guide through unfamiliar spaces
- **Daily life support**: Supports people with physical constraints

### 🏢 Ghost Concierge
- **Unmanned reception**: AI greets visitors during off-hours
- **After-hours service**: Provide information when staff unavailable
- **Multi-language support**: Global AWS Polly/Transcribe
- **Cost-effective**: No need for 24/7 staffing

### 🎭 Exhibition Guide
- **Optimal viewpoints**: Provides explanations from best camera angles
- **Character expression**: Use different voices and gestures for engagement
- **Interactive experience**: Answer visitor questions in real-time
- **On-demand explanations**: Detailed information when requested

### 🎪 Entertainment
- **Physical gestures**: Create character-driven AI performers
- **Multiple personalities**: Different voices and movement styles
- **Engaging interaction**: Visual + audio + movement creates presence

### 🌐 Multi-Location Communication
- **Single consciousness, multiple locations**: One AI across offices/stores
- **Instant presence**: Appear where needed instantly
- **Consistent service**: Same AI personality everywhere

## 📊 Project Structure

```
AgentShell/
├── strands_agent/              # Strands Agent Core
│   ├── __init__.py
│   ├── agentcore_app.py       # AgentCore application (deployment)
│   └── core.py                # Local agent execution
│
├── mcp_server/                 # MCP Server
│   ├── __init__.py
│   └── server.py              # FastMCP tool definitions
│                              # - CAMERA_PROFILE env selects camera
│                              # - Tools prefixed: camera1_, camera2_
│
├── camera_utils/               # Camera Control Utilities
│   ├── __init__.py
│   ├── ptz.py                 # PTZ control (ONVIF)
│   ├── aws_tts.py             # AWS Polly TTS
│   └── aws_stt.py             # AWS Transcribe STT
│
├── alexa_skill/                # Alexa Integration
│   ├── lambda_function.py     # Alexa Skill handler
│   └── interaction_model.json # Voice interaction model
│
├── services/go2rtc/           # Streaming Service
│   ├── config/
│   │   └── go2rtc.yaml        # Multi-camera stream config
│   └── docker-compose.yml     # Docker setup
│
├── config/                     # Configuration Files
│   └── strands.env.example    # Environment template
│
├── scripts/                    # Utility Scripts
│   ├── agentcore_launch.sh         # Deploy to AWS
│   ├── start_agentcore_local.sh    # Start AgentCore locally
│   ├── start_all_mcp_servers.sh    # Start all MCP servers
│   ├── start_ngrok.sh              # Start ngrok tunnel
│   ├── start_strands_system.sh     # Start complete system
│   ├── startup_commands.txt        # Reference commands
│   └── stop_all_mcp_servers.sh     # Stop all MCP servers
│
├── docs/                       # Documentation (see separate docs/)
│
├── pyproject.toml             # Python project configuration
├── Dockerfile                 # Docker image definition
├── .bedrock_agentcore.yaml.example
├── .env                       # Environment variables (local)
├── sample.env                 # Sample environment template
├── tsconfig.node.json         # TypeScript config (for auxiliary tools)
└── README.md                  # This file
```


## 🐛 Troubleshooting

### Camera 2 Not Recognized

**Symptoms**: `camera2_*` tools not available

**Solution**:
```bash
# 1. Check environment variable
cat .env | grep MCP_SERVER

# Should be (multi-camera):
# MCP_SERVER_URLS=http://127.0.0.1:9006/sse/,http://127.0.0.1:9007/sse/

# 2. Verify MCP servers running
lsof -i :9006
lsof -i :9007

# 3. Restart all services
bash scripts/stop_all_mcp_servers.sh
bash scripts/start_all_mcp_servers.sh
bash scripts/start_agentcore.sh
```

### Bedrock Access Denied

```bash
# Check available models
uv run python scripts/check_bedrock_access.py

# Verify AWS credentials
aws sts get-caller-identity

# Request model access in AWS Console
# Bedrock → Model access → Request access to Nova
```

### Camera Connection Failed

- Verify camera IP address and credentials
- Ensure ONVIF is enabled on camera
- Check camera and PC are on same network
- Test RTSP stream: `ffplay rtsp://user:pass@camera-ip:554/stream1`

## 📚 Documentation

- [Video Planning](docs/video_planning.md) - Demo scenario script
- [Multi-Camera Setup](docs/MULTI_CAMERA_SETUP.md) - Detailed multi-camera guide
- [Detailed Article](docs/article_20251018_en.md) - Full project documentation
- [Architecture](docs/architecture.md) - System architecture details

## 🎯 AWS AI Agent Hackathon

This project was built for the **AWS AI Agent Global Hackathon**.

### Requirements Checklist

- ✅ LLM hosted on AWS Bedrock (Amazon Bedrock Nova, Claude)
- ✅ Uses Strands SDK for agent building (AgentCore + agentic loop)
- ✅ Reasoning LLMs for autonomous decision-making
- ✅ External tool integration (MCP - redefined for physical control)
- ✅ Demonstrates practical real-world application
- ✅ Novel approach to embodied AI
- ✅ Measurable impact (privacy, cost savings, accessibility)

### Key Technologies & AWS Services Integration

- **Amazon Bedrock AgentCore**: Core agentic loop for autonomous decision-making
- **Strands Agents SDK**: Automates MCP tool selection and execution
- **Amazon Bedrock Nova (Micro/Pro)**: On-demand multimodal image analysis
- **AWS Polly (Neural TTS)**: Multiple voices for character expression (Matthew, Joanna, etc.)
- **AWS Transcribe**: Real-time speech recognition from camera microphones
- **Amazon S3**: Snapshot and history storage
- **MCP (Model Context Protocol)**: Redefined from data access to body control
- **FastMCP**: MCP server framework for rapid development

## 🌟 Scalability & Future Vision

### Current Status
- ✅ End-to-end functionality verified (Alexa trigger → camera selection → conversation loop)
- ✅ Tested with 2 cameras (living room + entrance)
- ✅ Secure architecture with no port exposure
- ✅ Autonomous tool selection via Strands Agents

### Easy Scale-Out
- **Add MCP server = Add body** (no code changes)
- Same agent, same policy, infinite cameras
- Theoretically unlimited expansion

### Future Vision
- 🗣️ Real Alexa voice trigger in production
- 📊 Dashboard for event timeline & snapshot history
- 🌍 Multi-language support (global AWS Polly/Transcribe)
- 🤖 Integration with smart home, robots, drones via MCP
- 🌐 Edge AI for low latency & offline operation
- 🎭 Character/personality modes for diverse applications
- 🔐 Enhanced privacy features for home use

## 🤝 Contributing

This is a hackathon project, but contributions and feedback are welcome!

## 📄 License

MIT License - see [LICENSE](LICENSE) file

## 🙏 Acknowledgments

- **AWS Bedrock Team** for powerful AI models
- **Strands SDK** for excellent agent framework
- **Model Context Protocol** for extensible tool system
- **FastMCP** for rapid MCP server development

---

**AgentShell — Not just context. Control.**

*Giving AI physical presence through the Model Context Protocol*
