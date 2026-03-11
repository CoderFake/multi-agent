"""File listing business logic — query indexed files from Milvus.

Usage:
    from app.services.file_service import file_svc

    response = await file_svc.list_files(request)
"""

import logging

from app.core.milvus import get_milvus_client
from app.schemas.files import FileInfo, ListFilesRequest, ListFilesResponse

logger = logging.getLogger(__name__)


class FileService:
    """File metadata operations against Milvus collections."""

    async def list_files(self, request: ListFilesRequest) -> ListFilesResponse:
        """List distinct indexed files across specified collections.

        Returns:
            ListFilesResponse with file metadata.
        """
        client = get_milvus_client()
        files: list[FileInfo] = []

        for collection_name in request.collection_names:
            if not client.has_collection(collection_name):
                logger.warning(f"Collection '{collection_name}' not found, skipping")
                continue

            try:
                results = client.query(
                    collection_name=collection_name,
                    filter="",
                    output_fields=["file_name"],
                    limit=request.limit,
                )

                seen: set[str] = set()
                for row in results:
                    fname = row.get("file_name", "")
                    if fname and fname not in seen:
                        seen.add(fname)
                        files.append(
                            FileInfo(name=fname, collection=collection_name)
                        )
            except Exception as e:
                logger.warning(f"Failed to list files from '{collection_name}': {e}")

        truncated = files[: request.limit]
        return ListFilesResponse(files=truncated, total=len(files))


# Module-level singleton
file_svc = FileService()

