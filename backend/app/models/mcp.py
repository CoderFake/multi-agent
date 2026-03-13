"""
CMS MCP Server and Tool models.
"""
import uuid
from sqlalchemy import Column, String, Boolean, Text, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.models.base import Base


class CmsMcpServer(Base):
    """
    MCP server registry. org_id=NULL → system MCP, org_id set → tenant MCP.
    """
    __tablename__ = "cms_mcp_server"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("cms_organization.id", ondelete="CASCADE"), nullable=True, index=True)
    codename = Column(String(255), unique=True, nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    transport = Column(String(50), nullable=False)  # stdio, sse, streamable-http
    connection_config = Column(JSONB, nullable=True)
    requires_env_vars = Column(Boolean, default=False, nullable=False)  # toggle: needs env vars from tenant
    is_active = Column(Boolean, default=True, nullable=False)
    is_public = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    def __repr__(self) -> str:
        return f"<CmsMcpServer(codename={self.codename})>"


class CmsTool(Base):
    """Tool provided by an MCP server."""
    __tablename__ = "cms_tool"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mcp_server_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_mcp_server.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    codename = Column(String(255), unique=True, nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    input_schema = Column(JSONB, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    def __repr__(self) -> str:
        return f"<CmsTool(codename={self.codename})>"
