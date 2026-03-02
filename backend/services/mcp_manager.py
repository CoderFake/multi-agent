import json
import asyncio
from typing import Dict, List, Any, Optional
from pathlib import Path
import uuid

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from schemas.agent import MCPConfig



class MCPManager:
    """Manages MCP configurations and loaded instances using FastMCP"""
    
    def __init__(self, storage_path: str = "./mcp_data"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        self.loaded_mcps: Dict[str, MCPConfig] = {}
        self.mcp_sessions: Dict[str, ClientSession] = {}
        self._lock = asyncio.Lock()
        
        self._load_persisted_mcps()
    
    def _load_persisted_mcps(self):
        """Load all persisted MCP configs from disk"""
        print("Loading persisted MCPs from disk...")
        for config_file in self.storage_path.glob("*.json"):
            try:
                with open(config_file, "r") as f:
                    config_data = json.load(f)
                    mcp_config = MCPConfig(**config_data)
                    self.loaded_mcps[mcp_config.id] = mcp_config
                    print(f"Loaded MCP: {mcp_config.name} ({len(mcp_config.tools)} tools)")
            except Exception as e:
                print(f"Failed to load {config_file}: {e}")
        
        print(f"Total loaded: {len(self.loaded_mcps)} MCPs")
    
    async def create_mcp_config(self, mcp_json: Dict[str, Any]) -> MCPConfig:
        """
        Create MCP config WITHOUT connecting (fast, for immediate response)
        Connection happens later in background
        
        PRESERVES original mcp_json structure to avoid parameter transformation bugs
        """
        async with self._lock:
            mcp_id = str(uuid.uuid4())
            protocol = mcp_json.get("protocol", "stdio")
            
            config = mcp_json.get("config", mcp_json)
            
            if protocol == "stdio":
                if "mcpServers" in config:
                    servers = config["mcpServers"]
                    server_name = list(servers.keys())[0] if servers else "unnamed"
                    server_config = servers.get(server_name, {})
                    name = mcp_json.get("name") or server_name
                    command = server_config.get("command", "node")
                    args = server_config.get("args", [])
                    env = server_config.get("env")
                    
                else:
                    name = mcp_json.get("name", f"MCP-{mcp_id[:8]}")
                    command = config.get("command", "node")
                    args = config.get("args", [])
                    env = config.get("env")
                
                parsed_config = {
                    "command": command,
                    "args": args,
                    "env": env,
                    "protocol": "stdio"
                }
            elif protocol == "sse" or protocol == "http":
                url = config.get("url")
                if not url:
                    raise ValueError("SSE/HTTP protocol requires 'url' field")
                name = mcp_json.get("name", f"SSE-MCP-{mcp_id[:8]}")
                headers = config.get("headers", {})
                parsed_config = {
                    "url": url,
                    "headers": headers,
                    "protocol": "sse"
                }
            else:
                raise ValueError(f"Unsupported protocol: {protocol}")
            
            mcp_config = MCPConfig(
                id=mcp_id,
                name=name,
                protocol=protocol,
                config=parsed_config,
                tools=[]
            )
            
            self.loaded_mcps[mcp_id] = mcp_config
            await self._save_mcp_config(mcp_config)
            
            return mcp_config
    
    async def connect_and_load_tools(self, mcp_config: MCPConfig):
        """
        Connect to MCP server and load tools (slow, run in background)
        PRESERVES exact inputSchema from MCP server without modification
        """
        try:
            protocol = mcp_config.protocol
            
            if protocol == "stdio":
                async with asyncio.timeout(60):
                    server_params = StdioServerParameters(
                        command=mcp_config.config["command"],
                        args=mcp_config.config["args"],
                        env=mcp_config.config.get("env")
                    )
                    
                    print(f"Connecting to stdio MCP: {mcp_config.config['command']} {' '.join(mcp_config.config['args'])}")
                    
                    async with stdio_client(server_params) as (read, write):
                        async with ClientSession(read, write) as session:
                            await session.initialize()
                            tools_result = await session.list_tools()
                            
                            print(f"Successfully connected! Found {len(tools_result.tools)} tools")
                            
                            mcp_config.tools = [
                                {
                                    "name": tool.name,
                                    "description": tool.description,
                                    "inputSchema": tool.inputSchema
                                }
                                for tool in tools_result.tools
                            ]
                            
                            await self._save_mcp_config(mcp_config)
                            
            elif protocol == "sse" or protocol == "http":
                from services.sse_transport import SSEMCPSession
                
                async with asyncio.timeout(60):
                    print(f"Connecting to SSE/HTTP MCP: {mcp_config.config['url']}")
                    
                    session = SSEMCPSession(
                        url=mcp_config.config["url"],
                        headers=mcp_config.config.get("headers")
                    )
                    
                    try:
                        await session.initialize()
                        tools_result = await session.list_tools()
                        
                        print(f"Successfully connected! Found {len(tools_result.tools)} tools")
                        
                        mcp_config.tools = [
                            {
                                "name": tool.name,
                                "description": tool.description,
                                "inputSchema": tool.inputSchema
                            }
                            for tool in tools_result.tools
                        ]
                        
                        await self._save_mcp_config(mcp_config)
                    finally:
                        await session.close()
                        
        except asyncio.TimeoutError:
            print(f"ERROR: Connection timeout for MCP {mcp_config.name}")
            mcp_config.tools = []
        except Exception as e:
            print(f"ERROR: Could not connect to MCP server: {e}")
            import traceback
            traceback.print_exc()
            mcp_config.tools = []


    async def import_mcp(self, mcp_json: Dict[str, Any]) -> MCPConfig:
        """
        Import MCP configuration from JSON and connect to MCP server
        
        Supports both formats:
        1. Claude Desktop format:
           {
             "mcpServers": {
               "server-name": {
                 "command": "...",
                 "args": [...]
               }
             }
           }
        2. Direct format:
           {
             "name": "...",
             "command": "...",
             "args": [...]
           }
        """
        async with self._lock:
            mcp_id = str(uuid.uuid4())
            
            protocol = mcp_json.get("protocol", "stdio")
            
            if protocol == "stdio":
                if "mcpServers" in mcp_json:
                    servers = mcp_json["mcpServers"]
                    server_name = list(servers.keys())[0]
                    server_config = servers[server_name]
                    
                    name = mcp_json.get("name", server_name)
                    command = server_config.get("command", "node")
                    args = server_config.get("args", [])
                    env = server_config.get("env")
                else:
                    name = mcp_json.get("name", f"MCP-{mcp_id[:8]}")
                    command = mcp_json.get("command", "node")
                    args = mcp_json.get("args", [])
                    env = mcp_json.get("env")
                
                server_params = StdioServerParameters(
                    command=command,
                    args=args,
                    env=env
                )
                
                print(f"Connecting to stdio MCP: {command} {' '.join(args)}")
                
                async with stdio_client(server_params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        tools_result = await session.list_tools()
                        
                        print(f"Successfully connected! Found {len(tools_result.tools)} tools")
                        
                        tools = [
                            {
                                "name": tool.name,
                                "description": tool.description,
                                "inputSchema": tool.inputSchema
                            }
                            for tool in tools_result.tools
                        ]
                        
                        mcp_config = MCPConfig(
                            id=mcp_id,
                            name=name,
                            protocol="stdio",
                            config={
                                "command": command,
                                "args": args,
                                "env": env,
                                "protocol": "stdio"
                            },
                            tools=tools
                        )
                        
                        self.loaded_mcps[mcp_id] = mcp_config
                        await self._save_mcp_config(mcp_config)
                        
                        return mcp_config
                        
            elif protocol == "sse" or protocol == "http":
                from services.sse_transport import SSEMCPSession
                
                url = mcp_json.get("url")
                if not url:
                    raise ValueError("SSE/HTTP protocol requires 'url' field")
                
                name = mcp_json.get("name", f"SSE-MCP-{mcp_id[:8]}")
                headers = mcp_json.get("headers", {})
                
                print(f"Connecting to SSE/HTTP MCP: {url}")
                
                session = SSEMCPSession(url, headers)
                
                try:
                    await session.initialize()
                    tools_result = await session.list_tools()
                    
                    print(f"Successfully connected! Found {len(tools_result.tools)} tools")
                    
                    tools = [
                        {
                            "name": tool.name,
                            "description": tool.description,
                            "inputSchema": tool.inputSchema
                        }
                        for tool in tools_result.tools
                    ]
                    
                    mcp_config = MCPConfig(
                        id=mcp_id,
                        name=name,
                        protocol="sse",
                        config={
                            "url": url,
                            "headers": headers,
                            "protocol": "sse"
                        },
                        tools=tools
                    )
                    
                    self.loaded_mcps[mcp_id] = mcp_config
                    await self._save_mcp_config(mcp_config)
                    
                    return mcp_config
                    
                finally:
                    await session.close()
            else:
                raise ValueError(f"Unsupported protocol: {protocol}")
    
    async def _save_mcp_config(self, mcp_config: MCPConfig):
        """Save MCP config to disk PRESERVING exact structure"""
        config_file = self.storage_path / f"{mcp_config.id}.json"
        
        config_dict = {
            "id": mcp_config.id,
            "name": mcp_config.name,
            "protocol": mcp_config.protocol,
            "config": mcp_config.config,
            "tools": mcp_config.tools
        }
        
        with open(config_file, "w") as f:
            json.dump(config_dict, f, indent=2)
    
    async def get_mcp(self, mcp_id: str) -> Optional[MCPConfig]:
        """Get MCP config by ID"""
        return self.loaded_mcps.get(mcp_id)
    
    async def list_mcps(self) -> List[MCPConfig]:
        """List all loaded MCPs"""
        return list(self.loaded_mcps.values())
    
    async def unload_mcp(self, mcp_id: str) -> bool:
        """Unload MCP and remove from system"""
        async with self._lock:
            if mcp_id in self.loaded_mcps:
                if mcp_id in self.mcp_sessions:
                    del self.mcp_sessions[mcp_id]
                
                del self.loaded_mcps[mcp_id]
                
                config_file = self.storage_path / f"{mcp_id}.json"
                if config_file.exists():
                    config_file.unlink()
                
                return True
            return False
    
    async def get_tools(self, mcp_id: str) -> List[Dict[str, Any]]:
        """Get tools for a specific MCP"""
        mcp = await self.get_mcp(mcp_id)
        if mcp:
            return mcp.tools
        return []
    
    async def invoke_tool(
        self, 
        mcp_id: str, 
        tool_name: str, 
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Invoke a tool from a specific MCP using FastMCP
        Supports both stdio and SSE/HTTP transports
        
        PRESERVES exact arguments structure - no field renaming
        """
        
        if isinstance(arguments, dict) and len(arguments) == 1 and 'kwargs' in arguments:
            arguments = arguments['kwargs']
        
        mcp = await self.get_mcp(mcp_id)
        if not mcp:
            raise ValueError(f"MCP {mcp_id} not found")
        
        try:
            if mcp.protocol == "stdio":
                command = mcp.config.get("command", "node")
                args = mcp.config.get("args", [])
                env = mcp.config.get("env")
                
                server_params = StdioServerParameters(
                    command=command,
                    args=args,
                    env=env
                )
                
                async with stdio_client(server_params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        result = await session.call_tool(tool_name, arguments)
                        
                        return {
                            "tool": tool_name,
                            "arguments": arguments,
                            "result": result.content,
                            "success": not result.isError
                        }
                        
            elif mcp.protocol == "sse" or mcp.protocol == "http":
                from services.sse_transport import SSEMCPSession
                
                url = mcp.config.get("url")
                headers = mcp.config.get("headers", {})
                
                session = SSEMCPSession(url, headers)
                
                try:
                    await session.initialize()
                    result = await session.call_tool(tool_name, arguments)
                    
                    return {
                        "tool": tool_name,
                        "arguments": arguments,
                        "result": result.content,
                        "success": not result.isError
                    }
                finally:
                    await session.close()
            else:
                raise NotImplementedError(f"Protocol {mcp.protocol} not yet implemented")
                
        except Exception as e:
            return {
                "tool": tool_name,
                "arguments": arguments,
                "error": str(e),
                "success": False
            }


mcp_manager = MCPManager()