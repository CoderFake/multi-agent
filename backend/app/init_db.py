"""
CLI entrypoint for database initialization.
Run: uv run python -m app.init_db

Delegates to modular sync functions in app.db_sync.
"""
import asyncio

from app.core.database import db_manager
from app.db_sync import (
    sync_permissions,
    sync_default_groups,
    sync_superuser,
    sync_providers,
    sync_models,
    sync_agents,
    sync_tool_servers,
    sync_tools,
    sync_settings,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def init_db() -> None:
    """Run all seed operations."""
    await db_manager.connect()

    try:
        async for db in db_manager.get_session():
            # 1. Permissions & groups
            perm_map = await sync_permissions(db)
            await sync_default_groups(db, perm_map)

            # 2. Providers & models
            provider_map = await sync_providers(db)
            await sync_models(db, provider_map)

            # 3. Tools (servers + tool definitions)
            server_map = await sync_tool_servers(db)
            await sync_tools(db, server_map)

            # 4. System agents
            await sync_agents(db)

            # 5. Superuser
            await sync_superuser(db)

            # 6. System settings
            await sync_settings(db)

            logger.info("Database initialization complete!")
            break
    finally:
        await db_manager.disconnect()


if __name__ == "__main__":
    asyncio.run(init_db())
