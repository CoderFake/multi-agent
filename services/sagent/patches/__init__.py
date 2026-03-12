"""Monkey patches for third-party packages.

This module applies patches to external dependencies that cannot be modified directly.
Import this module early in application startup (before the patched modules are used).

Current patches:
- ag_ui_adk.EventTranslator: Preserves thought/reasoning content with semantic tags
- google.adk.models.google_llm.Gemini: Auto-retries `429 RESOURCE_EXHAUSTED` errors
"""

from .thought_tags import apply_thought_tag_patch
from .retry_genai import apply_retry_patch

apply_thought_tag_patch()
apply_retry_patch()
