"""Bonus · Live MCP: the same Scout, a different data source.

build_scout() is the exact factory from step 1. We only swap its tools for an MCP toolset
that talks to a live football data server over SSE. The agent code does not change.
Demo only: the server allows 30 requests per minute per IP, so one person runs it.
"""

from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import SseConnectionParams

from steps.step1_scout.agent import build_scout

live_football = McpToolset(
    connection_params=SseConnectionParams(url="https://livescoremcp.com/sse", timeout=15),
    # The server has 16 tools; expose only the ones a scout needs, to keep the prompt small.
    tool_filter=["search", "get_team", "get_player", "get_match", "get_standings", "get_head_to_head"],
)

root_agent = build_scout(name="live_scout", tools=[live_football])
