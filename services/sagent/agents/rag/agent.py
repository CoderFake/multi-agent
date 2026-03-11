"""Team knowledge sub-agent for document retrieval.

This agent specialises in searching and browsing team knowledge bases via
the Milvus retrieval microservice. Communication happens over RabbitMQ
RPC queues (rag_requests → retrieval → reply queue).

Architecture:
    Root Agent → AgentTool(team_knowledge_agent) → RabbitMQ → Retrieval (Milvus)
                                                                  ↓
                                                   response queue → sagent
"""

import logging

from google.adk.agents import LlmAgent
from google.adk.tools import ToolContext

from config.settings import settings
from core.queue import rag_rpc
from instructions import team_knowledge_instruction

logger = logging.getLogger(__name__)


def _no_corpora_message(tool_context: ToolContext) -> str | None:
    """Return an error message if user has no accessible corpora, or None."""
    user_corpora = tool_context.state.get("user_corpora", [])

    if user_corpora:
        return None

    if not tool_context.state.get("_user_context_loaded"):
        logger.warning("User context not loaded - inject_user_context may not have run")
        return (
            "Unable to search: user context not initialised. "
            "Please try again or contact support if this persists."
        )

    user_teams = tool_context.state.get("user_teams", [])
    if not user_teams:
        return "No team memberships found. Contact your administrator to be added to a team."
    return f"Your teams ({', '.join(user_teams)}) don't have knowledge bases configured yet."


def search_knowledge(query: str, tool_context: ToolContext) -> str:
    """Search team knowledge bases for documents matching the query.

    Calls the Milvus retrieval microservice to perform vector search
    across all collections accessible to the current user.

    Args:
        query: The search query - what information to look for.
        tool_context: ADK tool context providing access to session state.

    Returns:
        Relevant document excerpts with source citations, or a message
        indicating no relevant information was found.
    """
    msg = _no_corpora_message(tool_context)
    if msg:
        return msg

    user_corpora = tool_context.state.get("user_corpora", [])

    try:
        data = rag_rpc.call("search", {
            "query": query,
            "collection_names": user_corpora,
            "top_k": settings.RAG_SIMILARITY_TOP_K,
        })

        if "error" in data:
            logger.error(f"RAG RPC error: {data['error']}")
            return "Knowledge search is temporarily unavailable. Please try again later."

        results_list = data.get("results", [])
        if not results_list:
            return f"No relevant documents found for: {query}"

        formatted = []
        for i, item in enumerate(results_list, 1):
            source = item.get("source", "Unknown source")
            text = item.get("text", "")
            score = item.get("score", 0)
            if text:
                source_name = source.split("/")[-1] if "/" in source else source
                formatted.append(f"[Source {i}: {source_name} (score: {score:.2f})]\n{text}")

        if not formatted:
            return f"No relevant documents found for: {query}"

        return "\n\n---\n\n".join(formatted)

    except (TimeoutError, ConnectionError) as e:
        logger.error(f"RAG RPC connection/timeout: {e}")
        return "Knowledge search is temporarily unavailable. Retrieval service not reachable."

    except Exception as e:
        logger.exception(f"RAG retrieval failed: {e}")
        return f"Error searching knowledge base: {str(e)}"


def list_knowledge_files(tool_context: ToolContext) -> str:
    """List files available in the user's team knowledge bases.

    Calls the retrieval microservice to list indexed documents.

    Args:
        tool_context: ADK tool context providing access to session state.

    Returns:
        A formatted list of available files, or a message if none found.
    """
    msg = _no_corpora_message(tool_context)
    if msg:
        return msg

    user_corpora = tool_context.state.get("user_corpora", [])

    try:
        data = rag_rpc.call("list_files", {
            "collection_names": user_corpora,
            "limit": 50,
        })

        if "error" in data:
            logger.error(f"RAG RPC error: {data['error']}")
            return "Knowledge base browsing is temporarily unavailable. Please try again later."

        files = data.get("files", [])
        total_count = data.get("total", len(files))

        if not files:
            return (
                "No files found in your team knowledge bases. "
                "Documents may not have been uploaded yet."
            )

        file_entries = [f"  - {f.get('name', 'Unknown')}" for f in files]

        if len(files) < total_count:
            header = (
                f"Showing {len(files)} of {total_count} files "
                f"(use search to find specific documents):\n\n"
            )
        else:
            header = f"Found {total_count} file(s) in your knowledge bases:\n\n"

        return header + "\n".join(file_entries)

    except (TimeoutError, ConnectionError) as e:
        logger.error(f"RAG RPC connection/timeout: {e}")
        return "Knowledge base browsing is temporarily unavailable. Retrieval service not reachable."

    except Exception as e:
        logger.exception(f"Failed to list knowledge files: {e}")
        return f"Error listing knowledge base files: {str(e)}"


# Create the team knowledge sub-agent
team_knowledge_agent = LlmAgent(
    name="team_knowledge_agent",
    model=settings.MODEL_RAG,
    description=(
        "Searches and browses team knowledge bases (documents synced from team GDrive folders). "
        "Use this agent when users ask about internal documents, policies, procedures, "
        "reports, GDrive files, or want to see what documents are available. "
        "This is the primary source for company knowledge."
    ),
    tools=[search_knowledge, list_knowledge_files],
    instruction=team_knowledge_instruction,
)
