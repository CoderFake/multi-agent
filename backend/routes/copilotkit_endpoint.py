"""
CopilotKit endpoint setup
Simplified endpoint file that uses the modular agent graph
"""

import logging
from fastapi import FastAPI
from copilotkit import LangGraphAGUIAgent
from ag_ui_langgraph import add_langgraph_fastapi_endpoint
from routes.agent.graph import create_agent_graph

logger = logging.getLogger(__name__)


async def setup_copilotkit(app: FastAPI):
    """
    Setup CopilotKit endpoint with the agent graph.
    
    Args:
        app: FastAPI application instance
    """
    logger.info("Setting up CopilotKit endpoint...")
    
    # Create the agent graph (async)
    graph = await create_agent_graph()
    
    # Create CopilotKit agent
    agent = LangGraphAGUIAgent(
        name="default",
        description="MCP-powered AI assistant with real-time state tracking",
        graph=graph,
    )
    
    # Add FastAPI endpoint
    add_langgraph_fastapi_endpoint(
        app=app,
        agent=agent,
        path="/copilotkit",
    )
    
    logger.info("CopilotKit endpoint setup complete at /copilotkit")
