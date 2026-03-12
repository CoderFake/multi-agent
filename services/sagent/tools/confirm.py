"""Confirmation tool for human-in-the-loop workflows."""

from google.adk.tools import ToolContext


async def request_confirmation(
    action_description: str,
    tool_name: str,
    tool_arguments: dict,
    tool_context: ToolContext,
) -> dict:
    """Call this tool ONLY when AUTO_APPROVE_MODE is OFF and you need to execute a tool.
    
    This renders a confirmation dialog to the user. You MUST WAIT for the user to approve before actually executing the target tool.
    
    Args:
        action_description: Clear explanation of what you are about to do (e.g. 'Search for weather in Hanoi').
        tool_name: The name of the tool you intend to call (e.g. 'web_search').
        tool_arguments: The exact arguments you plan to pass to the tool.
    
    Returns:
        A dictionary containing { "accepted": True | False }.
    """
    # This function is never fully executed on the backend because it's intercepted
    # by CopilotKit in the frontend (via useCopilotAction).
    # It just returns a pending status so the backend waits.
    return {
        "status": "awaiting_user_confirmation",
        "action_description": action_description,
        "tool_name": tool_name,
        "tool_arguments": tool_arguments,
    }
