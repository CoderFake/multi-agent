"""
Research canvas tool definitions used by chat_node.
Each @tool is a structured signal that the LLM returns as a tool_call.
"""

from typing import List
import logging

from langchain.tools import tool

logger = logging.getLogger(__name__)


@tool
def Search(queries: List[str]):  # pylint: disable=invalid-name,unused-argument
    """A list of one or more search queries to find good resources to support the research."""


@tool
def WriteReport(report: str):  # pylint: disable=invalid-name,unused-argument
    """Write the research report."""


@tool
def WriteResearchQuestion(research_question: str):  # pylint: disable=invalid-name,unused-argument
    """Write the research question."""


@tool
def DeleteResources(urls: List[str]):  # pylint: disable=invalid-name,unused-argument
    """Delete the URLs from the resources."""


def truncate_resources(resources: List[dict], max_chars: int = 15000) -> List[dict]:
    """
    Truncate resource content to prevent exceeding token limits.
    Distributes max_chars evenly across all resources.
    """
    if not resources:
        return resources

    total_chars = sum(len(r.get("content", "")) for r in resources)
    if total_chars <= max_chars:
        return resources

    chars_per = max_chars // len(resources)
    result = []
    for r in resources:
        content = r.get("content", "")
        if len(content) > chars_per:
            logger.warning(
                "Truncated resource %s: %d → %d chars",
                r.get("url", "?"), len(content), chars_per,
            )
            result.append({**r, "content": content[:chars_per] + "\n… [truncated]"})
        else:
            result.append(r)
    return result
