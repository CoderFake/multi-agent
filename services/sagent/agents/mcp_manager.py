"""Manager for MCP-based agents.

Reads mcp.json for each agent and returns McpToolset objects (Google ADK native).
If an agent does not have an mcp.json, the function returns [] gracefully.

Schema for mcp.json (compatible with both Gitlab MCP format and Claude Desktop format):

    {
      "mcpServers": {
        "server-name": {
          "type": "http" | "sse" | "stdio",   ← "type" or "transport" both accepted
          "url": "https://host/api/v4/mcp",    ← http / sse only
          "command": "docker",                  ← stdio only
          "args": ["run", "-i", "--rm", "img"], ← stdio only
          "token": "static-bearer-token",       ← optional (prefer runtime injection)
          "tool_filter": ["tool_a", "tool_b"],  ← optional whitelist
          "timeout": 30                         ← optional, default 30s
        }
      }
    }

Usage:
    # Static token (from mcp.json)
    tools = [existing_tool] + get_mcp_tools("agent_name")

    # Dynamic token (injected at request time — e.g. from user's OAuth record)
    tools = [existing_tool] + get_mcp_tools("agent_name", token="user-pat")
"""

import json
import logging
from pathlib import Path
from typing import Optional

from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import (
    SseConnectionParams,
    StdioConnectionParams,
    StreamableHTTPConnectionParams,
)
from mcp import StdioServerParameters

logger = logging.getLogger(__name__)

# Path to the mcp_agents directory
_MCP_AGENTS_DIR = Path(__file__).parent / "mcp_agents"


def _build_toolset(server_name: str, cfg: dict, token: Optional[str] = None) -> Optional[McpToolset]:
    """Build a single McpToolset from one server configuration block.

    Args:
        server_name: Name of the server (from mcpServers key)
        cfg: Server config dict from mcp.json
        token: Optional PAT/bearer token to override config (for per-user injection)
    """
    transport = (cfg.get("type") or cfg.get("transport") or "stdio").lower()
    tool_filter = cfg.get("tool_filter") or None

    bearer_token = token or cfg.get("token")

    try:
        if transport == "stdio":
            command = cfg.get("command")
            args = list(cfg.get("args", []))
            env = dict(cfg.get("env") or {})

            if not command:
                logger.warning("MCP server '%s': missing 'command' for stdio transport.", server_name)
                return None

            if bearer_token:
                token_env_key = cfg.get("token_env")
                if token_env_key:
                    env[token_env_key] = bearer_token
                elif "mcp-remote" in " ".join(args):
                    header_val = f"Authorization: Bearer {bearer_token}"
                    if "--header" not in args:
                        url_idx = next(
                            (i for i, a in enumerate(args) if a.startswith("http")),
                            len(args),
                        )
                        args.insert(url_idx, header_val)
                        args.insert(url_idx, "--header")
                else:
                    env["MCP_TOKEN"] = bearer_token

            connection = StdioConnectionParams(
                server_params=StdioServerParameters(
                    command=command,
                    args=args,
                    env=env if env else None,
                ),
                timeout=cfg.get("timeout", 30),
            )

        elif transport in ("sse", "http", "streamable_http"):
            url = cfg.get("url")
            if not url:
                logger.warning("MCP server '%s': missing 'url' for %s transport.", server_name, transport)
                return None

            headers = {}
            if bearer_token:
                headers["Authorization"] = f"Bearer {bearer_token}"

            if transport == "sse":
                connection = SseConnectionParams(
                    url=url,
                    headers=headers,
                    timeout=cfg.get("timeout", 30),
                    sse_read_timeout=cfg.get("sse_read_timeout", 300),
                )
            else:
                connection = StreamableHTTPConnectionParams(
                    url=url,
                    headers=headers,
                    timeout=cfg.get("timeout", 30),
                )

        else:
            logger.warning("MCP server '%s': unknown transport '%s', skipping.", server_name, transport)
            return None

        toolset = McpToolset(
            connection_params=connection,
            tool_filter=tool_filter,
        )
        logger.info("Built McpToolset for '%s' via %s transport.", server_name, transport)
        return toolset

    except Exception as e:
        logger.error("Failed to build McpToolset for server '%s': %s", server_name, e)
        return None


def _load_config(agent_name: str) -> Optional[dict]:
    """Read and parse the mcp.json for the given agent. Returns None if absent or invalid."""
    mcp_json_path = _MCP_AGENTS_DIR / agent_name / "mcp.json"

    if not mcp_json_path.exists():
        return None

    try:
        with open(mcp_json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Failed to read mcp.json for agent '%s': %s", agent_name, e)
        return None


def get_mcp_tools(agent_name: str, token: Optional[str] = None) -> list:
    """Loads MCP toolsets for the specified agent.

    Reads `agents/mcp_agents/{agent_name}/mcp.json` for configuration.
    Returns [] silently if no mcp.json is found or if mcpServers is empty.

    Composable usage:
        tools = [existing_tool] + get_mcp_tools("gitlab", token=user_pat)

    Args:
        agent_name: Name of the agent subdirectory (e.g. 'gitlab', 'search', 'data_analyst')
        token: Optional bearer token to inject into HTTP/SSE connections (per-user PAT).
               If provided, overrides the static "token" field in mcp.json.

    Returns:
        A list of McpToolset instances, or [].
    """
    config = _load_config(agent_name)
    if config is None:
        return []  # No mcp.json — silently skip

    servers = config.get("mcpServers", {})
    if not servers:
        return []  # Empty mcpServers — silently skip

    logger.info("Loading MCP toolsets for '%s': %d server(s).", agent_name, len(servers))

    toolsets = []
    for server_name, server_cfg in servers.items():
        toolset = _build_toolset(server_name, server_cfg, token=token)
        if toolset is not None:
            toolsets.append(toolset)

    return toolsets


# ==============================================================================
# Startup: Auto-pull stdio MCP Docker images
# ==============================================================================


def _find_stdio_docker_images() -> list:
    """Scan all mcp.json files and return list of (agent, server, image) for stdio docker servers."""
    images = []
    for mcp_json in sorted(_MCP_AGENTS_DIR.glob("*/mcp.json")):
        agent_name = mcp_json.parent.name
        try:
            config = json.loads(mcp_json.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("Startup MCP scan: failed to parse %s: %s", mcp_json, e)
            continue

        for server_name, cfg in config.get("mcpServers", {}).items():
            transport = (cfg.get("type") or cfg.get("transport") or "stdio").lower()
            if transport != "stdio":
                continue
            if cfg.get("command") != "docker":
                continue

            # Extract Docker image: first positional arg in ["run", "-i", "--rm", "<image>", ...]
            image = None
            skip_next = False
            for arg in cfg.get("args", []):
                if arg in ("run", "-i", "--rm", "-d", "--platform"):
                    continue
                if arg.startswith("--"):
                    skip_next = True
                    continue
                if arg.startswith("-"):
                    skip_next = True
                    continue
                if skip_next:
                    skip_next = False
                    continue
                image = arg
                break

            if image:
                images.append((agent_name, server_name, image))

    return images


async def pull_stdio_mcp_images() -> None:
    """Pull Docker images for all stdio MCP servers declared in mcp.json files.

    Called automatically on sagent startup (via FastAPI lifespan).
    Skipped gracefully if Docker is not available.
    """
    import asyncio
    import shutil
    import subprocess

    # Bail out if docker CLI is not on PATH
    if not shutil.which("docker"):
        logger.warning("MCP startup: 'docker' not found on PATH — skipping stdio MCP image pull.")
        return

    images = _find_stdio_docker_images()
    if not images:
        logger.debug("MCP startup: no stdio Docker MCP servers found — nothing to pull.")
        return

    logger.info("MCP startup: pulling %d Docker image(s) for stdio MCP servers...", len(images))

    async def pull_one(agent: str, server: str, image: str) -> None:
        logger.info("  [%s/%s] docker pull %s", agent, server, image)
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "pull", image,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()
            if proc.returncode == 0:
                logger.info("  ✓ [%s/%s] pulled %s", agent, server, image)
            else:
                err = stderr.decode().strip() if stderr else "unknown error"
                logger.warning("  ✗ [%s/%s] failed to pull %s: %s", agent, server, image, err)
        except Exception as e:
            logger.warning("  ✗ [%s/%s] docker pull %s raised: %s", agent, server, image, e)

    # Pull all images concurrently
    await asyncio.gather(*[pull_one(a, s, img) for a, s, img in images])
    logger.info("MCP startup: Docker image pull complete.")
