"""
CMS Provider models — LLM providers, API keys, models, and agent-provider mapping.
"""
import uuid
from sqlalchemy import Column, String, Boolean, Integer, Text, ForeignKey, DateTime, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.models.base import Base


class CmsProvider(Base):
    """LLM Provider registry (OpenAI, Gemini, Ollama...). org_id=NULL → system."""
    __tablename__ = "cms_provider"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("cms_organization.id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    api_base_url = Column(String(500), nullable=True)
    auth_type = Column(String(20), nullable=False)  # api_key, bearer, none
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)

    def __repr__(self) -> str:
        return f"<CmsProvider(slug={self.slug})>"


class CmsProviderKey(Base):
    """Encrypted API key per org per provider. List allows rotation."""
    __tablename__ = "cms_provider_key"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_provider.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    api_key_encrypted = Column(Text, nullable=False)
    priority = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    cooldown_until = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)


class CmsAgentModel(Base):
    """Model definition (gpt-4o, gemini-2.5-flash etc.)."""
    __tablename__ = "cms_agent_model"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_provider.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    model_type = Column(String(20), nullable=False)  # chat, embedding
    context_window = Column(Integer, nullable=True)
    pricing_per_1m_tokens = Column(Numeric(10, 4), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)

    def __repr__(self) -> str:
        return f"<CmsAgentModel(name={self.name})>"


class CmsAgentProvider(Base):
    """Agent ↔ Provider ↔ Model mapping per org."""
    __tablename__ = "cms_agent_provider"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_agent.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_provider.id", ondelete="CASCADE"),
        nullable=False,
    )
    model_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_agent_model.id", ondelete="CASCADE"),
        nullable=False,
    )
    config_override = Column(JSONB, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
