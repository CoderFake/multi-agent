from typing import Annotated, TypedDict, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.message import add_messages
from core.config import settings
from services.mcp_manager import mcp_manager


class AgentState(TypedDict):
    """State for the LangGraph agent"""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    pending_approval: bool
    pending_tool_call: dict | None


class ChatService:
    """
    Chat service with LangGraph human-in-the-loop support
    """
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            streaming=True
        )
        self.memory = MemorySaver()
        self.graph = None
        self._build_graph()
    
    def _build_graph(self):
        """Build LangGraph workflow with human-in-the-loop"""
        
        # Create graph
        workflow = StateGraph(AgentState)
        
        # Define nodes
        workflow.add_node("agent", self._agent_node)
        workflow.add_node("human_approval", self._human_approval_node)
        workflow.add_node("execute_tool", self._execute_tool_node)
        
        # Define edges
        workflow.set_entry_point("agent")
        
        # After agent, check if approval is needed
        workflow.add_conditional_edges(
            "agent",
            self._should_request_approval,
            {
                "approve": "human_approval",
                "execute": "execute_tool",
                "end": END
            }
        )
        
        # After human approval, execute or end
        workflow.add_conditional_edges(
            "human_approval",
            self._check_approval_status,
            {
                "approved": "execute_tool",
                "rejected": END,
                "pending": END  # Interrupt and wait
            }
        )
        
        # After tool execution, go back to agent
        workflow.add_edge("execute_tool", "agent")
        
        # Compile with checkpointer for interrupts
        self.graph = workflow.compile(
            checkpointer=self.memory,
            interrupt_before=["human_approval"]  # Interrupt before human approval
        )
    
    async def _agent_node(self, state: AgentState) -> AgentState:
        """Agent generates response or decides on tool usage"""
        
        all_tools = []
        mcps = await mcp_manager.list_mcps()
        
        print(f"DEBUG: Found {len(mcps)} MCPs")
        for mcp in mcps:
            print(f"DEBUG: MCP '{mcp.name}' has {len(mcp.tools)} tools")
            for tool in mcp.tools:
                langchain_tool = {
                    "type": "function",
                    "function": {
                        "name": tool.get("name"),
                        "description": tool.get("description", ""),
                        "parameters": tool.get("inputSchema", {})
                    }
                }
                all_tools.append(langchain_tool)
        
        print(f"DEBUG: Binding {len(all_tools)} tools to LLM")
        if all_tools:
            print(f"DEBUG: First tool: {all_tools[0]}")
        
        # Bind tools to LLM
        if all_tools:
            llm_with_tools = self.llm.bind_tools(all_tools)
        else:
            llm_with_tools = self.llm
        
        # Prepare messages with system prompt if not present
        from langchain_core.messages import SystemMessage
        messages = state["messages"]
        has_system = any(isinstance(msg, SystemMessage) for msg in messages)
        
        if not has_system:
            system_msg = SystemMessage(content="""You are a helpful AI assistant with access to various tools through MCP (Model Context Protocol).
            
When the user asks you something:
- If you need to use a tool, call it using the available functions
- Otherwise, respond directly to the user in a helpful and conversational way
- Always provide clear, concise, and accurate responses""")
            messages = [system_msg] + list(messages)
        
        # Generate response
        response = await llm_with_tools.ainvoke(messages)
        
        return {
            "messages": [response],
            "pending_approval": False,
            "pending_tool_call": None
        }
    
    def _should_request_approval(self, state: AgentState) -> str:
        """Decide if human approval is needed"""
        last_message = state["messages"][-1]
        
        # Check if the last message has tool calls
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            tool_call = last_message.tool_calls[0]
            
            # Request approval for certain sensitive operations
            # You can customize this logic based on your needs
            sensitive_tools = ["delete", "update", "modify"]
            if any(keyword in tool_call["name"].lower() for keyword in sensitive_tools):
                return "approve"
            else:
                return "execute"
        
        return "end"
    
    async def _human_approval_node(self, state: AgentState) -> AgentState:
        """Node that waits for human approval"""
        last_message = state["messages"][-1]
        
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            tool_call = last_message.tool_calls[0]
            
            return {
                "messages": state["messages"],
                "pending_approval": True,
                "pending_tool_call": tool_call
            }
        
        return state
    
    def _check_approval_status(self, state: AgentState) -> str:
        """Check if approval was granted"""
        if state.get("pending_approval"):
            return "pending"
        # This would be updated by external approval call
        return "approved"
    
    async def _execute_tool_node(self, state: AgentState) -> AgentState:
        """Execute the tool call"""
        last_message = state["messages"][-1]
        
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            tool_call = last_message.tool_calls[0]
            
            # Find which MCP has this tool
            mcps = await mcp_manager.list_mcps()
            mcp_id = None
            
            for mcp in mcps:
                if any(t.get("name") == tool_call["name"] for t in mcp.tools):
                    mcp_id = mcp.id
                    break
            
            if mcp_id:
                # Invoke the tool
                result = await mcp_manager.invoke_tool(
                    mcp_id,
                    tool_call["name"],
                    tool_call["args"]
                )
                
                # Parse MCP result properly
                ui_resource = None
                tool_content = ""
                
                # Handle different result types
                if isinstance(result, list):
                    # List of TextContent objects from MCP
                    text_parts = []
                    for item in result:
                        if hasattr(item, 'text'):
                            # TextContent object
                            text_parts.append(item.text)
                        elif isinstance(item, dict):
                            # Check for UIResource in dict
                            if "uiResource" in item or "ui_resource" in item:
                                ui_resource = item.get("uiResource") or item.get("ui_resource")
                            else:
                                text_parts.append(str(item))
                        else:
                            text_parts.append(str(item))
                    tool_content = "\n".join(text_parts)
                    
                elif isinstance(result, dict):
                    # Dict might contain UIResource
                    if "uiResource" in result:
                        ui_resource = result["uiResource"]
                        tool_content = str({k: v for k, v in result.items() if k != "uiResource"})
                    elif "ui_resource" in result:
                        ui_resource = result["ui_resource"]
                        tool_content = str({k: v for k, v in result.items() if k != "ui_resource"})
                    else:
                        tool_content = str(result)
                        
                elif hasattr(result, 'text'):
                    # Single TextContent object
                    tool_content = result.text
                else:
                    # Fallback
                    tool_content = str(result)
                
                # Create tool message with optional UIResource
                additional_kwargs = {}
                if ui_resource:
                    additional_kwargs["ui_resource"] = ui_resource
                
                tool_message = ToolMessage(
                    content=tool_content,
                    tool_call_id=tool_call["id"],
                    additional_kwargs=additional_kwargs
                )
                
                return {
                    "messages": [tool_message],
                    "pending_approval": False,
                    "pending_tool_call": None
                }
        
        return state

    
    async def stream_chat(self, message: str, thread_id: str = "default"):
        """
        Stream chat responses
        
        Args:
            message: User message
            thread_id: Thread ID for conversation history
            
        Yields:
            Chat events and responses
        """
        config = {"configurable": {"thread_id": thread_id}}
        
        # Add user message
        initial_state = {
            "messages": [HumanMessage(content=message)],
            "pending_approval": False,
            "pending_tool_call": None
        }
        
        # Stream events
        async for event in self.graph.astream(initial_state, config):
            yield event
    
    async def approve_action(self, thread_id: str, approved: bool):
        """
        Approve or reject a pending action
        
        Args:
            thread_id: Thread ID
            approved: Whether the action is approved
        """
        config = {"configurable": {"thread_id": thread_id}}
        
        # Get current state
        state = await self.graph.aget_state(config)
        
        # Update approval status
        if approved:
            # Continue execution
            updated_state = {
                **state.values,
                "pending_approval": False
            }
        else:
            # Reject - add rejection message
            updated_state = {
                **state.values,
                "pending_approval": False,
                "messages": state.values["messages"] + [
                    AIMessage(content="Action rejected by user.")
                ]
            }
        
        # Update state and continue
        await self.graph.aupdate_state(config, updated_state)
        
        # Continue execution if approved
        if approved:
            async for event in self.graph.astream(None, config):
                yield event


# Global chat service instance
chat_service = ChatService()
