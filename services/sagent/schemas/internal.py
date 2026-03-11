"""Internal endpoint schemas — RAG sync."""

from pydantic import BaseModel, Field


class SyncTrigger(BaseModel):
    """Request body for the sync endpoint."""

    trigger: str = Field(
        default="unknown",
        description="Trigger source identifier",
        examples=["scheduled", "manual"],
    )


class SyncResultItem(BaseModel):
    """Result of syncing a single team corpus."""

    team_id: str = Field(..., description="Team identifier")
    status: str = Field(..., description="Sync status (success/error)")
    file_count: int = Field(default=0, ge=0, description="Number of files processed")
    error: str | None = Field(default=None, description="Error message if failed")
    duration_seconds: float | None = Field(default=None, description="Duration of sync in seconds")


class SyncSummary(BaseModel):
    """Aggregate sync statistics."""

    total: int = Field(..., ge=0, description="Total corpora synced")
    succeeded: int = Field(..., ge=0, description="Number that succeeded")
    failed: int = Field(..., ge=0, description="Number that failed")
    duration_seconds: float = Field(..., description="Total sync duration in seconds")


class SyncResponse(BaseModel):
    """Response for the RAG sync endpoint."""

    success: bool = Field(..., description="Whether the overall sync succeeded")
    trigger: str = Field(..., description="What triggered this sync")
    summary: SyncSummary | None = Field(default=None, description="Aggregate statistics")
    results: list[SyncResultItem] = Field(default_factory=list, description="Per-corpus results")
    error: str | None = Field(default=None, description="Error message if overall sync failed")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "success": True,
                    "trigger": "scheduled",
                    "summary": {
                        "total": 3,
                        "succeeded": 3,
                        "failed": 0,
                        "duration_seconds": 12.5,
                    },
                    "results": [
                        {
                            "team_id": "eng_001",
                            "status": "success",
                            "file_count": 15,
                            "error": None,
                            "duration_seconds": 4.2,
                        }
                    ],
                }
            ]
        }
    }

