#!/usr/bin/env python3
"""Pull all Docker images required by stdio-transport MCP servers.

Scans every mcp.json file under services/sagent/agents/mcp_agents/*/
and pulls the Docker image for each server that:
  - uses stdio transport ("type" or "transport" key)
  - has "docker" as the command (i.e. docker run ... <image>)

Usage:
  python scripts/mcp_pull_images.py [--dry-run]
"""
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

MCP_AGENTS_DIR = Path(__file__).parent.parent / "services" / "sagent" / "agents" / "mcp_agents"


def find_stdio_docker_images() -> List[Dict]:

    """Returns list of {agent, server, image} for all stdio docker MCP configs."""
    images = []
    for mcp_json in sorted(MCP_AGENTS_DIR.glob("*/mcp.json")):
        agent_name = mcp_json.parent.name
        try:
            config = json.loads(mcp_json.read_text())
        except Exception as e:
            print(f"⚠  [{agent_name}] Failed to parse mcp.json: {e}", file=sys.stderr)
            continue

        for server_name, cfg in config.get("mcpServers", {}).items():
            transport = (cfg.get("type") or cfg.get("transport") or "stdio").lower()
            if transport != "stdio":
                continue
            command = cfg.get("command", "")
            args = cfg.get("args", [])
            if command != "docker":
                continue
            # Extract image name from args: ["run", "-i", "--rm", "<image>", ...]
            # Image is the first arg that doesn't start with "-" after "run"
            image = None
            skip_next = False
            for i, arg in enumerate(args):
                if arg in ("run", "-i", "--rm", "-d"):
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
                images.append({
                    "agent": agent_name,
                    "server": server_name,
                    "image": image,
                })

    return images


def main():
    dry_run = "--dry-run" in sys.argv
    images = find_stdio_docker_images()

    if not images:
        print("✓  No stdio Docker MCP servers found.")
        return

    print(f"\n{'DRY RUN: ' if dry_run else ''}Pulling {len(images)} MCP Docker image(s)...\n")
    errors = []

    for entry in images:
        image = entry["image"]
        agent = entry["agent"]
        server = entry["server"]
        print(f"  [{agent}/{server}] docker pull {image}")
        if dry_run:
            continue
        result = subprocess.run(["docker", "pull", image], capture_output=False)
        if result.returncode != 0:
            errors.append(f"  ✗ Failed to pull {image} (agent: {agent})")
        else:
            print(f"  ✓ Pulled {image}\n")

    if errors:
        print("\nErrors:")
        for e in errors:
            print(e)
        sys.exit(1)
    else:
        print("\n✓  All MCP Docker images ready.")


if __name__ == "__main__":
    main()
