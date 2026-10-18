"""
Tutor MCP client for DAIA.

Uses stdio transport — the backend container spawns the tutor-mcp binary
directly. This avoids the need for a separate HTTP server container.
"""

import os
import asyncio
import traceback

from langchain_mcp_adapters.client import MultiServerMCPClient

# Path to the binary inside the backend container (set in Dockerfile)
TUTOR_MCP_BINARY = os.getenv("TUTOR_MCP_BINARY", "/usr/local/bin/tutor-mcp")

_mcp_client: MultiServerMCPClient | None = None
_tutor_tools = None
_initialized = False
_init_lock = asyncio.Lock()


async def _ensure_initialized() -> None:
    """Initialize the MCP client and cache the tools once per process."""
    global _mcp_client, _tutor_tools, _initialized

    if _initialized and _tutor_tools is not None:
        return

    async with _init_lock:
        if _initialized and _tutor_tools is not None:
            return

        try:
            _mcp_client = MultiServerMCPClient(
                {
                    "tutor": {
                        "command": TUTOR_MCP_BINARY,
                        "args": ["--local"],
                        "transport": "stdio",
                    }
                }
            )
            _tutor_tools = await _mcp_client.get_tools()
            _initialized = True
            print(
                f"[TUTOR MCP] Loaded {len(_tutor_tools)} tools via stdio from {TUTOR_MCP_BINARY}.",
                flush=True,
            )
        except Exception as exc:
            print(f"[TUTOR MCP] Initialization failed: {exc}", flush=True)
            traceback.print_exc()
            _tutor_tools = []
            _initialized = True


def get_tutor_tools():
    """Return the cached LangChain tools (sync wrapper)."""
    if not _initialized:
        try:
            asyncio.get_running_loop()
            return _tutor_tools or []
        except RuntimeError:
            asyncio.run(_ensure_initialized())

    return _tutor_tools or []


async def call_tutor_tool(tool_name: str, arguments: dict):
    """Call a single Tutor MCP tool directly (used by the sidebar)."""
    await _ensure_initialized()

    if not _tutor_tools:
        raise RuntimeError(
            "Tutor MCP tools are not available. Check the binary path in the backend container."
        )

    tool = next((t for t in _tutor_tools if t.name == tool_name), None)
    if tool is None:
        available = ", ".join(t.name for t in _tutor_tools[:10])
        raise ValueError(
            f"Tool '{tool_name}' not found. Available examples: {available}"
        )

    return await tool.ainvoke(arguments)
