import logging
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from services.memory_service import memory_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/memories", tags=["memories"])


class SearchRequest(BaseModel):
    query: str
    user_id: str = "default_user"
    limit: int = 5


class AddMemoryRequest(BaseModel):
    messages: list[dict]
    user_id: str = "default_user"


@router.get("")
async def get_all_memories(user_id: str = Query(default="default_user")):
    """Get all memories for a user."""
    memories = await memory_service.get_all_memories(user_id=user_id)
    return {"memories": memories, "count": len(memories)}


@router.post("/search")
async def search_memories(request: SearchRequest):
    """Search memories by query."""
    memories = await memory_service.search_memories(
        query=request.query,
        user_id=request.user_id,
        limit=request.limit,
    )
    return {"results": memories, "count": len(memories)}


@router.post("")
async def add_memory(request: AddMemoryRequest):
    """Manually add a memory."""
    result = await memory_service.add_memory(
        messages=request.messages,
        user_id=request.user_id,
    )
    return result


@router.delete("/{memory_id}")
async def delete_memory(memory_id: str):
    """Delete a specific memory."""
    success = await memory_service.delete_memory(memory_id)
    if not success:
        raise HTTPException(status_code=404, detail="Memory not found or deletion failed")
    return {"status": "deleted", "memory_id": memory_id}


@router.delete("")
async def delete_all_memories(user_id: str = Query(default="default_user")):
    """Delete all memories for a user."""
    success = await memory_service.delete_all_memories(user_id=user_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete memories")
    return {"status": "deleted", "user_id": user_id}
