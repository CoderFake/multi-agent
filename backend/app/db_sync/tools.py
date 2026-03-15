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
            "input_schema": {"type": "object", "properties": {"search": {"type": "string"}, "owned": {"type": "boolean"}, "membership": {"type": "boolean"}}},
        },
        {
            "codename": "gitlab_list_issues",
            "display_name": "List Issues",
            "description": "List issues in a GitLab project.",
            "input_schema": {"type": "object", "properties": {"project_id": {"type": "string"}, "state": {"type": "string"}}, "required": ["project_id"]},
        },
        {
            "codename": "gitlab_create_issue",
            "display_name": "Create Issue",
            "description": "Create a new issue in a GitLab project.",
            "input_schema": {"type": "object", "properties": {"project_id": {"type": "string"}, "title": {"type": "string"}, "description": {"type": "string"}}, "required": ["project_id", "title"]},
        },
        {
            "codename": "gitlab_list_merge_requests",
            "display_name": "List Merge Requests",
            "description": "List merge requests in a GitLab project.",
            "input_schema": {"type": "object", "properties": {"project_id": {"type": "string"}, "state": {"type": "string"}}, "required": ["project_id"]},
        },
        {
            "codename": "gitlab_list_pipelines",
            "display_name": "List Pipelines",
            "description": "List recent CI/CD pipelines for a GitLab project.",
            "input_schema": {"type": "object", "properties": {"project_id": {"type": "string"}}, "required": ["project_id"]},
        },
    ],
    "mcp_redmine": [
        # ── Issues ──
        {
            "codename": "redmine_list_issues",
            "display_name": "List Issues",
            "description": "List Redmine issues with optional filters.",
            "input_schema": {"type": "object", "properties": {"project_id": {"type": "string"}, "status_id": {"type": "string"}, "assigned_to_id": {"type": "string"}, "tracker_id": {"type": "integer"}, "limit": {"type": "integer"}}},
        },
        {
            "codename": "redmine_get_issue",
            "display_name": "Get Issue",
            "description": "Get detailed information about a specific Redmine issue including comments and history.",
            "input_schema": {"type": "object", "properties": {"issue_id": {"type": "integer"}, "include": {"type": "string"}}, "required": ["issue_id"]},
        },
        {
            "codename": "create_issue",
            "display_name": "Create Issue",
            "description": "Create a new Redmine issue.",
            "input_schema": {"type": "object", "properties": {"project_id": {"type": "string"}, "subject": {"type": "string"}, "tracker_id": {"type": "integer"}, "priority_id": {"type": "integer"}}, "required": ["project_id", "subject"]},
        },
        {
            "codename": "redmine_update_issue",
            "display_name": "Update Issue",
            "description": "Update fields of an existing Redmine issue.",
            "input_schema": {"type": "object", "properties": {"issue_id": {"type": "integer"}, "subject": {"type": "string"}, "status_id": {"type": "integer"}}, "required": ["issue_id"]},
        },
        {
            "codename": "redmine_delete_issue",
            "display_name": "Delete Issue",
            "description": "Permanently delete a Redmine issue.",
            "input_schema": {"type": "object", "properties": {"issue_id": {"type": "integer"}}, "required": ["issue_id"]},
        },
        {
            "codename": "redmine_add_watcher",
            "display_name": "Add Watcher",
            "description": "Add a watcher to a Redmine issue.",
            "input_schema": {"type": "object", "properties": {"issue_id": {"type": "integer"}, "user_id": {"type": "integer"}}, "required": ["issue_id", "user_id"]},
        },
        {
            "codename": "redmine_remove_watcher",
            "display_name": "Remove Watcher",
            "description": "Remove a watcher from a Redmine issue.",
            "input_schema": {"type": "object", "properties": {"issue_id": {"type": "integer"}, "user_id": {"type": "integer"}}, "required": ["issue_id", "user_id"]},
        },
        {
            "codename": "redmine_list_relations",
            "display_name": "List Relations",
            "description": "List all relations of a Redmine issue.",
            "input_schema": {"type": "object", "properties": {"issue_id": {"type": "integer"}}, "required": ["issue_id"]},
        },
        {
            "codename": "redmine_create_relation",
            "display_name": "Create Relation",
            "description": "Create a relation between two Redmine issues.",
            "input_schema": {"type": "object", "properties": {"issue_id": {"type": "integer"}, "issue_to_id": {"type": "integer"}, "relation_type": {"type": "string"}}, "required": ["issue_id", "issue_to_id"]},
        },
        {
            "codename": "redmine_delete_relation",
            "display_name": "Delete Relation",
            "description": "Delete an issue relation.",
            "input_schema": {"type": "object", "properties": {"relation_id": {"type": "integer"}}, "required": ["relation_id"]},
        },
        {
            "codename": "redmine_list_categories",
            "display_name": "List Categories",
            "description": "List issue categories of a Redmine project.",
            "input_schema": {"type": "object", "properties": {"project_id": {"type": "string"}}, "required": ["project_id"]},
        },
        {
            "codename": "redmine_create_category",
            "display_name": "Create Category",
            "description": "Create a new issue category in a Redmine project.",
            "input_schema": {"type": "object", "properties": {"project_id": {"type": "string"}, "name": {"type": "string"}}, "required": ["project_id", "name"]},
        },
        # ── Projects ──
        {
            "codename": "redmine_list_projects",
            "display_name": "List Projects",
            "description": "List all accessible Redmine projects.",
            "input_schema": {"type": "object", "properties": {"limit": {"type": "integer"}, "include": {"type": "string"}}},
        },
        {
            "codename": "redmine_get_project",
            "display_name": "Get Project",
            "description": "Get details about a specific Redmine project.",
            "input_schema": {"type": "object", "properties": {"project_id": {"type": "string"}}, "required": ["project_id"]},
        },
        {
            "codename": "redmine_create_project",
            "display_name": "Create Project",
            "description": "Create a new Redmine project.",
            "input_schema": {"type": "object", "properties": {"name": {"type": "string"}, "identifier": {"type": "string"}}, "required": ["name", "identifier"]},
        },
        {
            "codename": "redmine_update_project",
            "display_name": "Update Project",
            "description": "Update a Redmine project.",
            "input_schema": {"type": "object", "properties": {"project_id": {"type": "string"}, "name": {"type": "string"}}, "required": ["project_id"]},
        },
        {
            "codename": "redmine_delete_project",
            "display_name": "Delete Project",
            "description": "Delete a Redmine project. This cannot be undone.",
            "input_schema": {"type": "object", "properties": {"project_id": {"type": "string"}}, "required": ["project_id"]},
        },
        {
            "codename": "redmine_archive_project",
            "display_name": "Archive Project",
            "description": "Archive or unarchive a Redmine project.",
            "input_schema": {"type": "object", "properties": {"project_id": {"type": "string"}, "archive": {"type": "boolean"}}, "required": ["project_id"]},
        },
        {
            "codename": "redmine_list_members",
            "display_name": "List Members",
            "description": "List members of a Redmine project.",
            "input_schema": {"type": "object", "properties": {"project_id": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["project_id"]},
        },
        {
            "codename": "redmine_list_versions",
            "display_name": "List Versions",
            "description": "List versions (milestones) of a Redmine project.",
            "input_schema": {"type": "object", "properties": {"project_id": {"type": "string"}}, "required": ["project_id"]},
        },
        {
            "codename": "redmine_create_version",
            "display_name": "Create Version",
            "description": "Create a new version (milestone) in a Redmine project.",
            "input_schema": {"type": "object", "properties": {"project_id": {"type": "string"}, "name": {"type": "string"}}, "required": ["project_id", "name"]},
        },
        # ── Time Entries ──
        {
            "codename": "redmine_list_time_entries",
            "display_name": "List Time Entries",
            "description": "List time entries logged in Redmine.",
            "input_schema": {"type": "object", "properties": {"project_id": {"type": "string"}, "issue_id": {"type": "integer"}, "user_id": {"type": "integer"}}},
        },
        {
            "codename": "log_time",
            "display_name": "Log Time",
            "description": "Log hours spent on a Redmine issue.",
            "input_schema": {"type": "object", "properties": {"issue_id": {"type": "integer"}, "hours": {"type": "number"}, "activity_id": {"type": "integer"}, "comments": {"type": "string"}}, "required": ["issue_id", "hours"]},
        },
        {
            "codename": "redmine_update_time_entry",
            "display_name": "Update Time Entry",
            "description": "Update an existing time entry.",
            "input_schema": {"type": "object", "properties": {"time_entry_id": {"type": "integer"}, "hours": {"type": "number"}}, "required": ["time_entry_id"]},
        },
        {
            "codename": "redmine_delete_time_entry",
            "display_name": "Delete Time Entry",
            "description": "Delete a time entry.",
            "input_schema": {"type": "object", "properties": {"time_entry_id": {"type": "integer"}}, "required": ["time_entry_id"]},
        },
        # ── Wiki ──
        {
            "codename": "redmine_list_wiki_pages",
            "display_name": "List Wiki Pages",
            "description": "List all wiki pages of a Redmine project.",
            "input_schema": {"type": "object", "properties": {"project_id": {"type": "string"}}, "required": ["project_id"]},
        },
        {
            "codename": "redmine_get_wiki_page",
            "display_name": "Get Wiki Page",
            "description": "Get content of a specific wiki page.",
            "input_schema": {"type": "object", "properties": {"project_id": {"type": "string"}, "title": {"type": "string"}}, "required": ["project_id", "title"]},
        },
        {
            "codename": "redmine_update_wiki_page",
            "display_name": "Update Wiki Page",
            "description": "Create or update a wiki page.",
            "input_schema": {"type": "object", "properties": {"project_id": {"type": "string"}, "title": {"type": "string"}, "text": {"type": "string"}}, "required": ["project_id", "title", "text"]},
        },
        {
            "codename": "redmine_delete_wiki_page",
            "display_name": "Delete Wiki Page",
            "description": "Delete a wiki page and its history.",
            "input_schema": {"type": "object", "properties": {"project_id": {"type": "string"}, "title": {"type": "string"}}, "required": ["project_id", "title"]},
        },
        # ── Enumerations & Lookup ──
        {
            "codename": "redmine_list_priorities",
            "display_name": "List Priorities",
            "description": "List all Redmine issue priority levels.",
            "input_schema": {},
        },
        {
            "codename": "redmine_list_trackers",
            "display_name": "List Trackers",
            "description": "List all Redmine trackers (Bug, Feature, Support, Task).",
            "input_schema": {},
        },
        {
            "codename": "redmine_list_statuses",
            "display_name": "List Statuses",
            "description": "List all Redmine issue statuses.",
            "input_schema": {},
        },
        {
            "codename": "redmine_list_activities",
            "display_name": "List Activities",
            "description": "List all Redmine time entry activity types.",
            "input_schema": {},
        },
        {
            "codename": "redmine_list_roles",
            "display_name": "List Roles",
            "description": "List all Redmine roles.",
            "input_schema": {},
        },
        {
            "codename": "redmine_list_queries",
            "display_name": "List Queries",
            "description": "List all saved custom queries.",
            "input_schema": {},
        },
        {
            "codename": "redmine_my_account",
            "display_name": "My Account",
            "description": "Get current user's account info.",
            "input_schema": {},
        },
        # ── Search ──
        {
            "codename": "redmine_search",
            "display_name": "Search",
            "description": "Search across Redmine for issues, projects, or wiki pages.",
            "input_schema": {"type": "object", "properties": {"q": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["q"]},
        },
        # ── Form ──
        {
            "codename": "request_user_input",
            "display_name": "Request User Input",
            "description": "Request form input from the user for creating or updating records.",
            "input_schema": {"type": "object", "properties": {"tool_name": {"type": "string"}, "project_id": {"type": "string"}, "options": {"type": "object"}, "form_defaults": {"type": "object"}}, "required": ["tool_name"]},
        },
    ],
}

# ── Agent ↔ Tool mapping ─────────────────────────────────────────────
# Maps agent codename → list of tool codenames it uses

AGENT_TOOLS: dict[str, list[str]] = {
    "team_knowledge_agent": ["search_knowledge", "list_knowledge_files"],
    "web_search": ["google_search"],
    "data_analyst_agent": ["query_data", "list_datasets", "describe_table", "create_chart"],
    "gitlab": [
        "gitlab_list_projects", "gitlab_list_issues", "gitlab_create_issue",
        "gitlab_list_merge_requests", "gitlab_list_pipelines",
    ],
    "redmine": [
        # Issues
        "redmine_list_issues", "redmine_get_issue", "create_issue",
        "redmine_update_issue", "redmine_delete_issue",
        "redmine_add_watcher", "redmine_remove_watcher",
        "redmine_list_relations", "redmine_create_relation", "redmine_delete_relation",
        "redmine_list_categories", "redmine_create_category",
        # Projects
        "redmine_list_projects", "redmine_get_project",
        "redmine_create_project", "redmine_update_project",
        "redmine_delete_project", "redmine_archive_project",
        "redmine_list_members", "redmine_list_versions", "redmine_create_version",
        # Time entries
        "redmine_list_time_entries", "log_time",
        "redmine_update_time_entry", "redmine_delete_time_entry",
        # Wiki
        "redmine_list_wiki_pages", "redmine_get_wiki_page",
        "redmine_update_wiki_page", "redmine_delete_wiki_page",
        # Enumerations & lookup
        "redmine_list_priorities", "redmine_list_trackers", "redmine_list_statuses",
        "redmine_list_activities", "redmine_list_roles", "redmine_list_queries",
        "redmine_my_account",
        # Search & forms
        "redmine_search", "request_user_input",
    ],
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
