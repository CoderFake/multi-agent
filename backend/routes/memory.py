import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from core.dependencies import get_current_user
from models.user import User
from services.memory_service import memory_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/memories", tags=["memories"])


class SearchRequest(BaseModel):
    query: str
    limit: int = 5


class AddMemoryRequest(BaseModel):
    messages: list[dict]


@router.get("")
async def get_all_memories(user: User = Depends(get_current_user)):
    """Get all memories for the authenticated user (keyed by UUIDv7 id)."""
    memories = await memory_service.get_all_memories(user_id=user.id)
    return {"memories": memories, "count": len(memories)}


@router.post("/search")
async def search_memories(
    request: SearchRequest,
    user: User = Depends(get_current_user),
):
    """Search memories by query."""
    memories = await memory_service.search_memories(
        query=request.query,
        user_id=user.id,
        limit=request.limit,
    )
    return {"results": memories, "count": len(memories)}


@router.post("")
async def add_memory(
    request: AddMemoryRequest,
    user: User = Depends(get_current_user),
):
    """Manually add a memory."""
    result = await memory_service.add_memory(
        messages=request.messages,
        user_id=user.id,
    )
    return result


@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: str,
    user: User = Depends(get_current_user),
):
    """Delete a specific memory."""
    success = await memory_service.delete_memory(memory_id)
    if not success:
        raise HTTPException(status_code=404, detail="Memory not found or deletion failed")
    return {"status": "deleted", "memory_id": memory_id}


@router.delete("")
async def delete_all_memories(user: User = Depends(get_current_user)):
    """Delete all memories for the authenticated user."""
    success = await memory_service.delete_all_memories(user_id=user.id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete memories")
    return {"status": "deleted", "user_id": user.id}
