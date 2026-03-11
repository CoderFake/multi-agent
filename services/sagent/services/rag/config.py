"""RAG configuration.

Provides chunking configuration for the retrieval microservice.
Reads values from centralised settings.
"""

import logging

from config.settings import settings

logger = logging.getLogger(__name__)

# Default chunking parameters
DEFAULT_CHUNK_SIZE = settings.RAG_CHUNK_SIZE
DEFAULT_CHUNK_OVERLAP = settings.RAG_CHUNK_OVERLAP
