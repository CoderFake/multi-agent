"""
DB Sync: System Agents.
Seeds common/system agent definitions derived from the sagent service.
Safe to run repeatedly — idempotent upsert.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import CmsAgent
from app.utils.datetime_utils import now
from app.utils.logging import get_logger

logger = get_logger(__name__)

# ── System agent definitions ──────────────────────────────────────────
# These correspond to agents in services/sagent/agents/
# org_id = NULL → system agents available to all orgs
#
# codename:     unique identifier, matches the agent "name" in sagent
# display_name: human-readable name shown in CMS UI
# description:  what the agent does
# default_config:  default configuration (model, tools, etc.)

SYSTEM_AGENTS = [
    {
        "codename": "team_knowledge_agent",
        "display_name": "Knowledge Search",
        "description": (
            "Searches and browses team knowledge bases (documents synced from shared folders). "
            "Use for internal documents, policies, procedures, reports, or listing available files."
        ),
        "default_config": {
            "model": "gemini-2.5-flash",
            "tools": ["search_knowledge", "list_knowledge_files"],
        },
    },
    {
        "codename": "web_search",
        "display_name": "Web Search",
        "description": (
            "Searches the web using Google Search for real-time information, "
            "news, technical documentation, and public knowledge."
        ),
        "default_config": {
            "model": "gemini-2.5-flash",
            "tools": ["google_search"],
        },
    },
    {
        "codename": "data_analyst_agent",
        "display_name": "Data Analyst",
        "description": (
            "Analyzes data and creates visualizations. Can query databases, "
            "process datasets, and generate charts and reports."
        ),
        "default_config": {
            "model": "gemini-2.5-pro",
            "tools": ["query_data", "list_datasets", "describe_table", "create_chart"],
        },
    },
    {
        "codename": "gitlab",
        "display_name": "GitLab",
        "description": (
            "Interacts with GitLab for project management, code reviews, "
            "merge requests, issues, and repository operations. "
            "Requires OAuth connection."
        ),
        "default_config": {
            "model": "gemini-2.5-flash",
            "tools": ["mcp:gitlab"],
            "requires_oauth": True,
            "oauth_provider": "gitlab",
        },
    },
    {
        "codename": "redmine",
        "display_name": "Redmine",
        "description": (
            "Interacts with Redmine for project management, issue tracking, "
            "time logging, and wiki. Requires OAuth/API key connection."
        ),
        "default_config": {
            "model": "gemini-2.5-flash",
            "tools": ["mcp:redmine"],
            "requires_oauth": True,
            "oauth_provider": "redmine",
        },
    },
]


async def sync_agents(db: AsyncSession) -> None:
    """
    Sync system agent definitions.
    Creates new agents, updates existing ones.
    Does NOT delete agents removed from the list (they may be enabled by orgs).
    """
    added, updated = 0, 0

    for adef in SYSTEM_AGENTS:
        result = await db.execute(
            select(CmsAgent).where(CmsAgent.codename == adef["codename"])
        )
        agent = result.scalar_one_or_none()

        if not agent:
            agent = CmsAgent(
                org_id=None,  # system agent
                codename=adef["codename"],
                display_name=adef["display_name"],
                description=adef["description"],
                default_config=adef["default_config"],
                is_active=True,
                created_at=now(),
            )
            db.add(agent)
            added += 1
            logger.info(f"  + Agent: {adef['codename']} ({adef['display_name']})")
        else:
            changed = False
            if agent.display_name != adef["display_name"]:
                agent.display_name = adef["display_name"]
                changed = True
            if agent.description != adef["description"]:
                agent.description = adef["description"]
                changed = True
            if agent.default_config != adef["default_config"]:
                agent.default_config = adef["default_config"]
                changed = True
            if changed:
                updated += 1
                logger.info(f"  ~ Agent updated: {adef['codename']}")

    await db.flush()
    await db.commit()
    logger.info(f"Agents synced: {len(SYSTEM_AGENTS)} total, {added} added, {updated} updated")
