#!/bin/bash
# AgentCoreランタイムをローカルで起動するスクリプト

echo "🚀 Starting BedrockAgentCore Runtime (Local Mode)..."

# プロジェクトルートディレクトリに移動
cd "$(dirname "$0")/.." || exit 1

# 環境変数をロード
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# ポート番号を環境変数で設定（AgentCore Runtime要件: 8080）
export PORT=8080

# AgentCoreランタイムをローカルモードで起動
echo "📍 AgentCore Runtime starting on port $PORT..."
echo "📝 Entrypoint: strands_agent/agentcore_app.py"
echo "🔧 MCP Servers: $MCP_SERVER_URLS"
echo ""
echo "Available endpoints:"
echo "  GET  http://localhost:$PORT/ping"
echo "  POST http://localhost:$PORT/invocations"
echo ""
uv run python strands_agent/agentcore_app.py
