"""
DB Sync: Providers & Models.
Seeds LLM provider definitions and their supported models.
Safe to run repeatedly — idempotent upsert.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.provider import CmsProvider, CmsAgentModel
from app.utils.datetime_utils import now
from app.utils.logging import get_logger

logger = get_logger(__name__)

# ── Provider definitions ──────────────────────────────────────────────
# System-level providers (org_id = NULL)
# slug must be unique, used for lookups

PROVIDERS = [
    {
        "slug": "google",
        "name": "Google AI / Vertex AI",
        "api_base_url": "https://generativelanguage.googleapis.com",
        "auth_type": "api_key",
    },
    {
        "slug": "openai",
        "name": "OpenAI",
        "api_base_url": "https://api.openai.com/v1",
        "auth_type": "bearer",
    },
    {
        "slug": "anthropic",
        "name": "Anthropic",
        "api_base_url": "https://api.anthropic.com/v1",
        "auth_type": "api_key",
    },
    {
        "slug": "ollama",
        "name": "Ollama (Self-hosted)",
        "api_base_url": "http://localhost:11434",
        "auth_type": "none",
    },
]

# ── Model definitions per provider ────────────────────────────────────
# model_type: "chat" or "embedding"
# context_window: max tokens (approximate)
# pricing_per_1m_tokens: USD per 1M tokens (input price, approximate)

MODELS: dict[str, list[dict]] = {
    "google": [
        # Gemini 3.x series (2026)
        {"name": "gemini-3.1-pro",           "model_type": "chat",      "context_window": 2097152, "pricing": 2.50},
        {"name": "gemini-3-flash",           "model_type": "chat",      "context_window": 1048576, "pricing": 0.20},
        {"name": "gemini-3.1-flash-lite",    "model_type": "chat",      "context_window": 1048576, "pricing": 0.10},
        # Gemini 2.5 series
        {"name": "gemini-2.5-pro",           "model_type": "chat",      "context_window": 1048576, "pricing": 1.25},
        {"name": "gemini-2.5-flash",         "model_type": "chat",      "context_window": 1048576, "pricing": 0.15},
        # Embedding
        {"name": "text-embedding-004",       "model_type": "embedding", "context_window": 2048,    "pricing": 0.006},
    ],
    "openai": [
        # GPT-5 series (2026)
        {"name": "gpt-5.4",                  "model_type": "chat",      "context_window": 1000000, "pricing": 1.25},
        {"name": "gpt-5.4-pro",              "model_type": "chat",      "context_window": 1000000, "pricing": 15.00},
        {"name": "gpt-5-mini",               "model_type": "chat",      "context_window": 400000,  "pricing": 0.125},
        {"name": "gpt-5-nano",               "model_type": "chat",      "context_window": 400000,  "pricing": 0.025},
        # GPT-4.1 series
        {"name": "gpt-4.1",                  "model_type": "chat",      "context_window": 1047576, "pricing": 3.50},
        {"name": "gpt-4.1-mini",             "model_type": "chat",      "context_window": 1047576, "pricing": 0.70},
        # o-series (reasoning, 2026)
        {"name": "o4-mini",                  "model_type": "chat",      "context_window": 200000,  "pricing": 2.00},
        {"name": "o3",                       "model_type": "chat",      "context_window": 200000,  "pricing": 3.50},
        # Embedding
        {"name": "text-embedding-3-small",   "model_type": "embedding", "context_window": 8191,    "pricing": 0.02},
        {"name": "text-embedding-3-large",   "model_type": "embedding", "context_window": 8191,    "pricing": 0.13},
    ],
    "anthropic": [
        # Claude 4 series (2026)
        {"name": "claude-opus-4-6",            "model_type": "chat",      "context_window": 200000,  "pricing": 5.00},
        {"name": "claude-sonnet-4-6",          "model_type": "chat",      "context_window": 200000,  "pricing": 3.00},
        {"name": "claude-haiku-4-5",           "model_type": "chat",      "context_window": 200000,  "pricing": 1.00},
        # Claude 3.7 (still active)
        {"name": "claude-3-7-sonnet-20250219", "model_type": "chat",      "context_window": 200000,  "pricing": 3.00},
    ],
    "ollama": [
        {"name": "llama3.3:70b",             "model_type": "chat",      "context_window": 131072,  "pricing": 0},
        {"name": "qwen3:14b",                "model_type": "chat",      "context_window": 131072,  "pricing": 0},
        {"name": "deepseek-r1:32b",          "model_type": "chat",      "context_window": 131072,  "pricing": 0},
        {"name": "gemma3:12b",               "model_type": "chat",      "context_window": 131072,  "pricing": 0},
        {"name": "nomic-embed-text",         "model_type": "embedding", "context_window": 8192,    "pricing": 0},
    ],
}


async def sync_providers(db: AsyncSession) -> dict[str, "CmsProvider"]:
    """
    Sync provider definitions. Creates new providers, updates existing ones.
    Returns a map of slug → CmsProvider for model seeding.
    """
    current_time = now()
    provider_map: dict[str, CmsProvider] = {}

    for pdef in PROVIDERS:
        result = await db.execute(
            select(CmsProvider).where(CmsProvider.slug == pdef["slug"])
        )
        provider = result.scalar_one_or_none()

        if not provider:
            provider = CmsProvider(
                org_id=None,
                slug=pdef["slug"],
                name=pdef["name"],
                api_base_url=pdef["api_base_url"],
                auth_type=pdef["auth_type"],
                is_active=True,
                created_at=current_time,
            )
            db.add(provider)
            await db.flush()
            logger.info(f"  + Provider: {pdef['name']} ({pdef['slug']})")
        else:
            # Update fields if changed
            changed = False
            if provider.name != pdef["name"]:
                provider.name = pdef["name"]
                changed = True
            if provider.api_base_url != pdef["api_base_url"]:
                provider.api_base_url = pdef["api_base_url"]
                changed = True
            if provider.auth_type != pdef["auth_type"]:
                provider.auth_type = pdef["auth_type"]
                changed = True
            if changed:
                logger.info(f"  ~ Provider updated: {pdef['slug']}")

        provider_map[pdef["slug"]] = provider

    await db.commit()
    logger.info(f"Providers synced: {len(provider_map)} total")
    return provider_map


async def sync_models(db: AsyncSession, provider_map: dict[str, "CmsProvider"]) -> None:
    """
    Sync model definitions for each provider.
    Creates new models, updates existing ones.
    Does NOT delete models removed from the list (they may be in use).
    """
    current_time = now()
    total_added, total_updated = 0, 0

    for provider_slug, models in MODELS.items():
        provider = provider_map.get(provider_slug)
        if not provider:
            logger.warning(f"Provider '{provider_slug}' not found, skipping models")
            continue

        for mdef in models:
            result = await db.execute(
                select(CmsAgentModel).where(
                    CmsAgentModel.provider_id == provider.id,
                    CmsAgentModel.name == mdef["name"],
                )
            )
            model = result.scalar_one_or_none()

            if not model:
                model = CmsAgentModel(
                    provider_id=provider.id,
                    name=mdef["name"],
                    model_type=mdef["model_type"],
                    context_window=mdef.get("context_window"),
                    pricing_per_1m_tokens=mdef.get("pricing"),
                    is_active=True,
                    created_at=current_time,
                )
                db.add(model)
                total_added += 1
                logger.info(f"  + Model: {provider_slug}/{mdef['name']}")
            else:
                changed = False
                if model.model_type != mdef["model_type"]:
                    model.model_type = mdef["model_type"]
                    changed = True
                if model.context_window != mdef.get("context_window"):
                    model.context_window = mdef.get("context_window")
                    changed = True
                if changed:
                    total_updated += 1
                    logger.info(f"  ~ Model updated: {provider_slug}/{mdef['name']}")

    await db.flush()
    await db.commit()
    logger.info(f"Models synced: {total_added} added, {total_updated} updated")
