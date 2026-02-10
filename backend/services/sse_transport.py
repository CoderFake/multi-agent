"""
SSE/HTTP transport for MCP
Based on Streamable HTTP specification
"""
import asyncio
import httpx
import json
from typing import AsyncIterator, Optional
from mcp import types


class SSETransport:
    """
    Streamable HTTP transport for MCP
    Handles communication with remote MCP servers via HTTP POST + optional SSE
    """
    
    def __init__(self, url: str, headers: Optional[dict] = None):
        self.url = url.rstrip('/')
        self.headers = headers or {}
        self.client = httpx.AsyncClient(timeout=300.0)
    
    async def send_request(self, request: dict) -> AsyncIterator[dict]:
        """
        Send a JSON-RPC request to the MCP server
        
        Args:
            request: JSON-RPC request object
            
        Yields:
            Response messages (may be multiple if using SSE streaming)
        """
        # Send POST request
        response = await self.client.post(
            f"{self.url}/mcp/v1",
            json=request,
            headers={
                "Content-Type": "application/json",
                "Accept": "text/event-stream, application/json",
                **self.headers
            }
        )
        
        response.raise_for_status()
        
        content_type = response.headers.get("content-type", "")
        
        if "text/event-stream" in content_type:
            current_data = []
            
            async for line in response.aiter_lines():
                line = line.strip()
                
                if line.startswith(':'):
                    continue
                
                if line.startswith('data:'):
                    data = line[5:].lstrip()
                    current_data.append(data)
                
                elif line == '' and current_data:
                    full_data = '\n'.join(current_data)
                    current_data = []
                    
                    if full_data:
                        try:
                            yield json.loads(full_data)
                        except json.JSONDecodeError as e:
                            print(f"Warning: Failed to parse SSE data as JSON: {e}")
                            continue
            
            if current_data:
                full_data = '\n'.join(current_data)
                if full_data:
                    try:
                        yield json.loads(full_data)
                    except json.JSONDecodeError:
                        pass
        else:
            yield response.json()
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


class SSEMCPSession:
    """
    MCP Client Session using SSE/HTTP transport
    Mimics the interface of mcp.ClientSession but for HTTP-based servers
    """
    
    def __init__(self, url: str, headers: Optional[dict] = None):
        self.transport = SSETransport(url, headers)
        self._request_id = 0
    
    def _next_request_id(self) -> int:
        """Generate next request ID"""
        self._request_id += 1
        return self._request_id
    
    async def initialize(self):
        """Initialize the MCP session"""
        request = {
            "jsonrpc": "2.0",
            "id": self._next_request_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "fastmcp-chat",
                    "version": "0.1.0"
                }
            }
        }
        
        async for response in self.transport.send_request(request):
            if "result" in response:
                return response["result"]
            elif "error" in response:
                raise Exception(f"Initialize failed: {response['error']}")
    
    async def list_tools(self) -> types.ListToolsResult:
        """List available tools from the MCP server"""
        request = {
            "jsonrpc": "2.0",
            "id": self._next_request_id(),
            "method": "tools/list",
            "params": {}
        }
        
        async for response in self.transport.send_request(request):
            if "result" in response:
                # Convert to MCP types
                tools = []
                for tool_data in response["result"].get("tools", []):
                    tool = types.Tool(
                        name=tool_data["name"],
                        description=tool_data.get("description", ""),
                        inputSchema=tool_data.get("inputSchema", {})
                    )
                    tools.append(tool)
                
                return types.ListToolsResult(tools=tools)
            elif "error" in response:
                raise Exception(f"List tools failed: {response['error']}")
    
    async def call_tool(self, name: str, arguments: dict) -> types.CallToolResult:
        """Call a tool on the MCP server"""
        request = {
            "jsonrpc": "2.0",
            "id": self._next_request_id(),
            "method": "tools/call",
            "params": {
                "name": name,
                "arguments": arguments
            }
        }
        
        async for response in self.transport.send_request(request):
            if "result" in response:
                result_data = response["result"]
                return types.CallToolResult(
                    content=[types.TextContent(text=json.dumps(result_data))],
                    isError=False
                )
            elif "error" in response:
                return types.CallToolResult(
                    content=[types.TextContent(text=response["error"]["message"])],
                    isError=True
                )
    
    async def close(self):
        """Close the session"""
        await self.transport.close()
