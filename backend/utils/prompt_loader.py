"""
utils/prompt_loader.py — Load and render prompts from static/prompts/*.yml

Usage:
    from utils.prompt_loader import load_prompt, render_prompt

    # Get raw template string
    template = load_prompt("system")                    # loads system.yml → "template" key
    template = load_prompt("memory_extraction", key="prompt")  # custom key

    # Render with variables
    text = render_prompt("system", instructions_section="...", research_context="...")
"""

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from core.config import PROMPTS_DIR

logger = logging.getLogger(__name__)


@lru_cache(maxsize=None)
def _load_yaml(name: str) -> dict:
    """
    Load a YAML file from static/prompts/<name>.yml.
    Results are cached (lru_cache) so each file is read once per process start.
    """
    path = PROMPTS_DIR / f"{name}.yml"
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    logger.debug("Loaded prompt: %s", path)
    return data or {}


def load_prompt(name: str, *, key: str = "template") -> str:
    """
    Load a prompt string from static/prompts/<name>.yml.

    Args:
        name: Filename without extension (e.g. "system", "memory_instructions")
        key:  YAML key to read (default: "template"; use "prompt" for mem0 prompts)

    Returns:
        Raw template string (may contain {variable} placeholders).

    Raises:
        FileNotFoundError: if the YAML file does not exist.
        KeyError: if the requested key is not present in the YAML.
    """
    data = _load_yaml(name)
    if key not in data:
        raise KeyError(f"Key '{key}' not found in prompt '{name}.yml'. Available: {list(data.keys())}")
    return data[key]


def render_prompt(name: str, *, key: str = "template", **variables: Any) -> str:
    """
    Load and render a prompt template with given variables.

    Args:
        name:      Filename without extension.
        key:       YAML key (default: "template").
        **variables: Values to substitute into {placeholder} slots.

    Returns:
        Rendered string with all {placeholder} values replaced.
        Unknown placeholders are left as-is (no KeyError raised).
    """
    template = load_prompt(name, key=key)
    try:
        # Use str.format_map with a defaultdict-like fallback so
        # missing variables don't raise and are left as "{var}"
        return template.format_map(_SafeDict(variables))
    except Exception as e:
        logger.warning("Error rendering prompt '%s': %s", name, e)
        return template


def reload_prompts() -> None:
    """Clear the YAML cache — call after editing prompt files in development."""
    _load_yaml.cache_clear()
    logger.info("Prompt cache cleared")


class _SafeDict(dict):
    """dict subclass that returns '{key}' for missing keys instead of raising."""
    def __missing__(self, key: str) -> str:
        return f"{{{key}}}"
