from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks
from typing import List
import json

from models.schemas import (
    MCPImportRequest,
    MCPResponse,
    MCPConfig
)
from services.mcp_manager import mcp_manager

router = APIRouter(prefix="/api/mcp", tags=["MCP Management"])


async def connect_mcp_background(mcp_config: MCPConfig):
    """Background task to connect to MCP and load tools"""
    try:
        await mcp_manager.connect_and_load_tools(mcp_config)
        print(f"Background: Successfully connected MCP {mcp_config.name}")
    except Exception as e:
        print(f"Background: Failed to connect MCP {mcp_config.name}: {e}")


@router.post("/import", response_model=MCPResponse)
async def import_mcp(request: MCPImportRequest, background_tasks: BackgroundTasks):
    """
    Import MCP configuration from JSON
    
    Returns immediately with MCP info, then connects in background
    PRESERVES exact structure to avoid parameter transformation
    """
    try:
        mcp_json = {
            "name": request.name or f"MCP-{request.protocol}",
            "protocol": request.protocol,
            "config": request.config
        }
        
        mcp_config = await mcp_manager.create_mcp_config(mcp_json)
        
        background_tasks.add_task(connect_mcp_background, mcp_config)
        
        return MCPResponse(
            id=mcp_config.id,
            name=mcp_config.name,
            protocol=mcp_config.protocol,
            tools_count=0
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/import/file", response_model=MCPResponse)
async def import_mcp_file(file: UploadFile = File(...)):
    """
    Import MCP configuration from uploaded JSON file
    PRESERVES exact JSON structure from file
    """
    try:
        content = await file.read()
        mcp_json = json.loads(content)
        
        mcp_config = await mcp_manager.import_mcp(mcp_json)
        
        return MCPResponse(
            id=mcp_config.id,
            name=mcp_config.name,
            protocol=mcp_config.protocol,
            tools_count=len(mcp_config.tools)
        )
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/list", response_model=List[MCPResponse])
async def list_mcps():
    """List all loaded MCP configurations"""
    mcps = await mcp_manager.list_mcps()
    return [
        MCPResponse(
            id=mcp.id,
            name=mcp.name,
            protocol=mcp.protocol,
            tools_count=len(mcp.tools)
        )
        for mcp in mcps
    ]


@router.get("/{mcp_id}", response_model=MCPConfig)
async def get_mcp(mcp_id: str):
    """Get detailed information about a specific MCP"""
    mcp = await mcp_manager.get_mcp(mcp_id)
    if not mcp:
        raise HTTPException(status_code=404, detail="MCP not found")
    return mcp


@router.delete("/{mcp_id}")
async def unload_mcp(mcp_id: str):
    """Unload and remove an MCP configuration"""
    success = await mcp_manager.unload_mcp(mcp_id)
    if not success:
        raise HTTPException(status_code=404, detail="MCP not found")
    return {"message": "MCP unloaded successfully"}


@router.get("/{mcp_id}/tools")
async def get_mcp_tools(mcp_id: str):
    """Get all tools available in a specific MCP"""
    tools = await mcp_manager.get_tools(mcp_id)
    if tools is None:
        raise HTTPException(status_code=404, detail="MCP not found")
    return {"tools": tools}