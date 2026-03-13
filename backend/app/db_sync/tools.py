"""
DB Sync: Tools & MCP Servers.
Seeds built-in tools used by system agents into the database.
Tools are stored under virtual "MCP servers" grouped by category.

Future: sagent's mcp_manager registry will auto-sync custom/MCP tools
to this DB table on startup, replacing the current JSON-file approach.
See services/sagent/agents/mcp_manager.py for the registry that will
connect to the CMS backend DB and call sync_tools() to keep tools in sync.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mcp import CmsMcpServer, CmsTool
from app.utils.datetime_utils import now
from app.utils.logging import get_logger

logger = get_logger(__name__)

# ── Virtual MCP servers (tool categories) ─────────────────────────────
# Non-MCP tools are grouped under virtual "servers" for DB organization.
# Real MCP servers (gitlab, redmine) are also registered here.

TOOL_SERVERS = [
    {
        "codename": "builtin",
        "display_name": "Built-in Tools",
        "transport": "native",
        "connection_config": {"type": "native", "note": "ADK built-in tools, no external server"},
    },
    {
        "codename": "knowledge",
        "display_name": "Knowledge Base",
        "transport": "native",
        "connection_config": {"type": "rpc", "queue": "rag_requests"},
    },
    {
        "codename": "data_analyst",
        "display_name": "Data Analyst",
        "transport": "native",
        "connection_config": {"type": "native", "note": "BigQuery integration tools"},
    },
    {
        "codename": "mcp_gitlab",
        "display_name": "GitLab MCP",
        "transport": "stdio",
        "connection_config": {"type": "mcp", "requires_oauth": True, "oauth_provider": "gitlab"},
    },
    {
        "codename": "mcp_redmine",
        "display_name": "Redmine MCP",
        "transport": "stdio",
        "connection_config": {"type": "mcp", "requires_oauth": True, "oauth_provider": "redmine"},
    },
]

# ── Tool definitions per server ───────────────────────────────────────
# codename: unique tool identifier
# display_name: human-readable name
# description: what the tool does
# input_schema: JSON schema for tool parameters (simplified)

TOOLS: dict[str, list[dict]] = {
    "builtin": [
        {
            "codename": "list_files",
            "display_name": "List Files",
            "description": "List files uploaded by the user in the current session.",
            "input_schema": {},
        },
        {
            "codename": "read_file",
            "display_name": "Read File",
            "description": "Read content of a file uploaded by the user.",
            "input_schema": {"type": "object", "properties": {"filename": {"type": "string"}}},
        },
        {
            "codename": "google_search",
            "display_name": "Google Search",
            "description": "Search the web using Google for current information, news, and facts.",
            "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}},
        },
    ],
    "knowledge": [
        {
            "codename": "search_knowledge",
            "display_name": "Search Knowledge",
            "description": (
                "Search team knowledge bases (documents synced from shared folders) "
                "for relevant information using vector similarity search."
            ),
            "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
        },
        {
            "codename": "list_knowledge_files",
            "display_name": "List Knowledge Files",
            "description": "List available files in the user's team knowledge bases.",
            "input_schema": {},
        },
    ],
    "data_analyst": [
        {
            "codename": "query_data",
            "display_name": "Query Data",
            "description": "Execute a SQL query against BigQuery datasets and return results.",
            "input_schema": {
                "type": "object",
                "properties": {"sql": {"type": "string"}, "dataset": {"type": "string"}},
                "required": ["sql"],
            },
        },
        {
            "codename": "list_datasets",
            "display_name": "List Datasets",
            "description": "List available BigQuery datasets and their tables.",
            "input_schema": {},
        },
        {
            "codename": "describe_table",
            "display_name": "Describe Table",
            "description": "Get schema and sample data for a BigQuery table.",
            "input_schema": {
                "type": "object",
                "properties": {"dataset": {"type": "string"}, "table": {"type": "string"}},
                "required": ["dataset", "table"],
            },
        },
        {
            "codename": "create_chart",
            "display_name": "Create Chart",
            "description": "Create a data visualization chart from query results.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "chart_type": {"type": "string", "enum": ["bar", "line", "pie", "scatter"]},
                    "data": {"type": "object"},
                    "title": {"type": "string"},
                },
                "required": ["chart_type", "data"],
            },
        },
    ],
    # MCP tools are auto-discovered at runtime.
    # These are placeholder entries so they appear in the UI.
    # The actual tool list will be synced from sagent's mcp_manager in the future.
    "mcp_gitlab": [
        {
            "codename": "gitlab_list_projects",
            "display_name": "List Projects",
            "description": "List GitLab projects accessible to the user.",
            "input_schema": {},
        },
        {
            "codename": "gitlab_list_issues",
            "display_name": "List Issues",
            "description": "List issues in a GitLab project.",
            "input_schema": {"type": "object", "properties": {"project_id": {"type": "string"}}},
        },
        {
            "codename": "gitlab_list_merge_requests",
            "display_name": "List Merge Requests",
            "description": "List merge requests in a GitLab project.",
            "input_schema": {"type": "object", "properties": {"project_id": {"type": "string"}}},
        },
    ],
    "mcp_redmine": [
        {
            "codename": "redmine_list_projects",
            "display_name": "List Projects",
            "description": "List Redmine projects accessible to the user.",
            "input_schema": {},
        },
        {
            "codename": "redmine_list_issues",
            "display_name": "List Issues",
            "description": "List issues in a Redmine project with filters.",
            "input_schema": {"type": "object", "properties": {"project_id": {"type": "string"}}},
        },
        {
            "codename": "redmine_log_time",
            "display_name": "Log Time",
            "description": "Log time spent on a Redmine issue.",
            "input_schema": {
                "type": "object",
                "properties": {"issue_id": {"type": "string"}, "hours": {"type": "number"}},
                "required": ["issue_id", "hours"],
            },
        },
    ],
}

# ── Agent ↔ Tool mapping ─────────────────────────────────────────────
# Maps agent codename → list of tool codenames it uses

AGENT_TOOLS: dict[str, list[str]] = {
    "team_knowledge_agent": ["search_knowledge", "list_knowledge_files"],
    "web_search": ["google_search"],
    "data_analyst_agent": ["query_data", "list_datasets", "describe_table", "create_chart"],
    "gitlab": ["gitlab_list_projects", "gitlab_list_issues", "gitlab_list_merge_requests"],
    "redmine": ["redmine_list_projects", "redmine_list_issues", "redmine_log_time"],
}


async def sync_tool_servers(db: AsyncSession) -> dict[str, CmsMcpServer]:
    """
    Sync virtual MCP server entries (tool categories).
    Returns map of codename → CmsMcpServer for tool seeding.
    """
    current_time = now()
    server_map: dict[str, CmsMcpServer] = {}

    for sdef in TOOL_SERVERS:
        result = await db.execute(
            select(CmsMcpServer).where(CmsMcpServer.codename == sdef["codename"])
        )
        server = result.scalar_one_or_none()

        if not server:
            server = CmsMcpServer(
                org_id=None,
                codename=sdef["codename"],
                display_name=sdef["display_name"],
                transport=sdef["transport"],
                connection_config=sdef.get("connection_config"),
                is_active=True,
                created_at=current_time,
            )
            db.add(server)
            await db.flush()
            logger.info(f"  + Tool Server: {sdef['codename']} ({sdef['display_name']})")
        else:
            changed = False
            if server.display_name != sdef["display_name"]:
                server.display_name = sdef["display_name"]
                changed = True
            if server.connection_config != sdef.get("connection_config"):
                server.connection_config = sdef.get("connection_config")
                changed = True
            if changed:
                logger.info(f"  ~ Tool Server updated: {sdef['codename']}")

        server_map[sdef["codename"]] = server

    await db.commit()
    logger.info(f"Tool servers synced: {len(server_map)} total")
    return server_map


async def sync_tools(db: AsyncSession, server_map: dict[str, CmsMcpServer]) -> None:
    """
    Sync tool definitions under each server.
    Creates new tools, updates existing ones.
    Does NOT delete tools removed from the list.

    NOTE — Future auto-sync from sagent:
    ─────────────────────────────────────
    In the future, sagent's mcp_manager._registry will connect to the
    CMS backend DB on startup and automatically sync discovered MCP tools
    into this table. The flow will be:

        sagent startup → mcp_manager discovers tools from MCP servers
                       → calls CMS API: POST /api/v1/system/tools/sync
                       → backend upserts tools in cms_tool table

    This replaces the current approach of loading tool definitions from
    JSON config files. The seed data here serves as the initial bootstrap
    until the auto-sync mechanism is implemented.
    """
    current_time = now()
    total_added, total_updated = 0, 0

    for server_codename, tools in TOOLS.items():
        server = server_map.get(server_codename)
        if not server:
            logger.warning(f"Tool server '{server_codename}' not found, skipping tools")
            continue

        for tdef in tools:
            result = await db.execute(
                select(CmsTool).where(CmsTool.codename == tdef["codename"])
            )
            tool = result.scalar_one_or_none()

            if not tool:
                tool = CmsTool(
                    mcp_server_id=server.id,
                    codename=tdef["codename"],
                    display_name=tdef["display_name"],
                    description=tdef.get("description"),
                    input_schema=tdef.get("input_schema"),
                    is_active=True,
                    created_at=current_time,
                )
                db.add(tool)
                total_added += 1
                logger.info(f"  + Tool: {tdef['codename']} ({server_codename})")
            else:
                changed = False
                if tool.display_name != tdef["display_name"]:
                    tool.display_name = tdef["display_name"]
                    changed = True
                if tool.description != tdef.get("description"):
                    tool.description = tdef.get("description")
                    changed = True
                if tool.input_schema != tdef.get("input_schema"):
                    tool.input_schema = tdef.get("input_schema")
                    changed = True
                if tool.mcp_server_id != server.id:
                    tool.mcp_server_id = server.id
                    changed = True
                if changed:
                    total_updated += 1
                    logger.info(f"  ~ Tool updated: {tdef['codename']}")

    await db.flush()
    await db.commit()
    logger.info(f"Tools synced: {total_added} added, {total_updated} updated")
