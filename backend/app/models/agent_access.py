"""
CMS Agent Access Control models.
Group → Agent, Agent → MCP, Group → Tool access.
"""
import uuid
from sqlalchemy import Column, Boolean, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.models.base import Base


class CmsAgentMcpServer(Base):
    """M2M: Which MCP servers are assigned to an agent within an org."""
    __tablename__ = "cms_agent_mcp_server"

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
    mcp_server_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_mcp_server.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_active = Column(Boolean, default=True, nullable=False)
    env_overrides = Column(JSONB, nullable=True)  # e.g. {"API_KEY": "value"}
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    def __repr__(self) -> str:
        return f"<CmsAgentMcpServer(agent={self.agent_id}, mcp={self.mcp_server_id})>"


class CmsOrgMcpServer(Base):
    """M2M: Which system MCP servers are assigned to which organizations."""
    __tablename__ = "cms_org_mcp_server"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mcp_server_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_mcp_server.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    def __repr__(self) -> str:
        return f"<CmsOrgMcpServer(org={self.org_id}, mcp={self.mcp_server_id})>"


class CmsGroupAgent(Base):
    """M2M: Which groups can use which agents (skipped if agent is_public)."""
    __tablename__ = "cms_group_agent"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_group.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_agent.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime(timezone=True), nullable=False)

    def __repr__(self) -> str:
        return f"<CmsGroupAgent(group={self.group_id}, agent={self.agent_id})>"


class CmsGroupToolAccess(Base):
    """M2M: Toggle tool access per group. No record = allowed (public default)."""
    __tablename__ = "cms_group_tool_access"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_group.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tool_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_tool.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)

    def __repr__(self) -> str:
        return f"<CmsGroupToolAccess(group={self.group_id}, tool={self.tool_id}, enabled={self.is_enabled})>"
