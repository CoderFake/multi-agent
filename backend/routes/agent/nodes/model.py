"""
Model selection module
Get appropriate LLM based on configuration
"""

import logging
from langchain_core.language_models.chat_models import BaseChatModel
from backend.core.config import settings
from backend.routes.agent.state import AgentState

logger = logging.getLogger(__name__)


def get_model(state: AgentState = None, tools: list = None) -> BaseChatModel:
    """
    Get a model based on the configuration settings.
    Optionally bind tools if provided.
    
    Args:
        state: AgentState (optional, for future extensibility)
        tools: List of tools to bind to the model
        
    Returns:
        BaseChatModel with optional tools bound
    """
    provider = settings.provider.lower()
    
    logger.info(f"Initializing {provider} model: {settings.model}")
    
    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        
        llm = ChatGoogleGenerativeAI(
            model=settings.model,
            temperature=0.7,
            google_api_key=settings.gemini_api_key,
            convert_system_message_to_human=True
        )
        
        if tools:
            # Filter Gemini-compatible tools
            compatible_tools = []
            logger.info(f"Testing {len(tools)} tools for Gemini compatibility...")
            for tool in tools:
                try:
                    llm.bind_tools([tool])
                    compatible_tools.append(tool)
                except Exception as e:
                    logger.warning(f"Skipping incompatible tool '{tool.name}': {str(e)[:100]}")
            
            logger.info(f"{len(compatible_tools)}/{len(tools)} tools compatible with Gemini")
            return llm.bind_tools(compatible_tools) if compatible_tools else llm
        
        return llm
    
    elif provider == "ollama":
        from langchain_ollama import ChatOllama
        
        llm = ChatOllama(
            model=settings.model,
            base_url=settings.ollama_base_url,
            temperature=0.7,
        )
        
        if tools:
            return llm.bind_tools(tools)
        
        return llm
        
    else:  # OpenAI
        from langchain_openai import ChatOpenAI
        
        llm = ChatOpenAI(
            model=settings.model,
            temperature=0.7,
            api_key=settings.openai_api_key,
            streaming=True,
            timeout=300
        )
        
        if tools:
            return llm.bind_tools(tools)
        
        return llm
