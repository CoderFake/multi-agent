"""Instruction providers for ADK agents.

This module loads prompts from YAML files in instructions/prompts/
and injects dynamic context (current date, user info) before each model call.

Prompt files live in: instructions/prompts/<name>.yml
Each YAML file has:
  system: |
    <system prompt — used by InstructionProvider functions>
  user: |
    <user prompt template — accessed via load_user_prompt()>

Usage:
    from instructions import root_instruction, load_user_prompt

    title_prompt = load_user_prompt("titles")
"""

from datetime import datetime
from pathlib import Path

import yaml
from google.adk.agents.readonly_context import ReadonlyContext

INSTRUCTIONS_DIR = Path(__file__).parent
PROMPTS_DIR = INSTRUCTIONS_DIR / "prompts"


# ── Private helpers ──────────────────────────────────────────────────────


def _load_yaml_prompt(name: str, role: str = "system") -> str:
    """Load a prompt string from a YAML file.

    Args:
        name: Prompt name (matches filename: prompts/<name>.yml).
        role: Key to read from the YAML — "system" or "user".

    Returns:
        The prompt string, or empty string if key is missing.
    """
    path = PROMPTS_DIR / f"{name}.yml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data.get(role, "") if isinstance(data, dict) else ""


def _inject_context(template: str, context: ReadonlyContext) -> str:
    """Replace placeholders with dynamic values.

    Placeholders:
        {{current_date}} -> "10 March 2026"
        {{current_year}} -> "2026"
        {{user_name}}    -> User's name from state, or empty string
    """
    now = datetime.now()

    replacements = {
        "{{current_date}}": now.strftime("%d %B %Y"),
        "{{current_year}}": str(now.year),
        "{{user_name}}": context.state.get("user:name", ""),
    }

    result = template
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, value)

    return result


# ── Public: InstructionProvider functions (used by LlmAgent.instruction=) ──


def root_instruction(context: ReadonlyContext) -> str:
    """InstructionProvider for the root agent."""
    return _inject_context(_load_yaml_prompt("root"), context)


def search_instruction(context: ReadonlyContext) -> str:
    """InstructionProvider for the web search agent."""
    return _inject_context(_load_yaml_prompt("search"), context)


def team_knowledge_instruction(context: ReadonlyContext) -> str:
    """InstructionProvider for the team knowledge (RAG) agent."""
    return _inject_context(_load_yaml_prompt("team_knowledge"), context)


def data_analyst_instruction(context: ReadonlyContext) -> str:
    """InstructionProvider for the data analyst (BigQuery) agent."""
    return _inject_context(_load_yaml_prompt("data_analyst"), context)


def gitlab_instruction(context: ReadonlyContext) -> str:
    """InstructionProvider for the gitlab agent."""
    return _inject_context(_load_yaml_prompt("gitlab"), context)


def redmine_instruction(context: ReadonlyContext) -> str:
    """InstructionProvider for the Redmine agent."""
    return _inject_context(_load_yaml_prompt("redmine"), context)


# ── Public: user prompt loader (used by services that call LLMs directly) ──


def load_user_prompt(name: str) -> str:
    """Load a user-role prompt template from a YAML file.

    Args:
        name: Prompt name (matches filename: prompts/<name>.yml).

    Returns:
        The user prompt string. May contain {variable} placeholders
        for str.format() substitution by the caller.
    """
    return _load_yaml_prompt(name, role="user")
