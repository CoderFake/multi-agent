from typing import AsyncGenerator
import logging
import asyncio

from google.adk.models.google_llm import Gemini
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai.errors import ClientError

logger = logging.getLogger("sagent.patches.retry_genai")

_original_generate_content_async = Gemini.generate_content_async

async def _patched_generate_content_async(
    self, llm_request: LlmRequest, stream: bool = False
) -> AsyncGenerator[LlmResponse, None]:
    max_retries = 2
    base_delay = 2

    for attempt in range(max_retries + 1):
        try:
            agen = _original_generate_content_async(self, llm_request, stream)
            async for chunk in agen:
                yield chunk
            return
        except ClientError as e:
            if e.code == 429 and attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                logger.warning(
                    f"Caught 429 RESOURCE_EXHAUSTED. Retrying in {delay} seconds (Attempt {attempt + 1}/{max_retries})..."
                )
                await asyncio.sleep(delay)
            else:
                raise

def apply_retry_patch():
    """Monkey patches Gemini.generate_content_async to append an explicit retry on 429 errors."""
    Gemini.generate_content_async = _patched_generate_content_async
    logger.info("Applied retry patch to Gemini.generate_content_async for 429 errors.")
