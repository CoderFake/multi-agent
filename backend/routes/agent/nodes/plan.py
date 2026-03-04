"""
Plan Node — synthesizes context + available MCP tools into a HITL-approved execution plan.

Flow:
  chat_node (initial response) → [document_node] → [knowledge_node] → [search_node]
       → plan_node   ← build plan from all gathered context + MCP tool list
       → interrupt() ← HITL: user sees plan in ApprovalCard (type=approval)
       → mcp_tools   (approved) | chat_node (rejected/empty plan)

LangGraph interrupt() pattern:
  - First execution: plan is generated, stored in state.execution_plan, interrupt() pauses graph
  - On resume: interrupt() returns user's decision; plan already in state (no re-generation)
  - Command(goto=...) routes to mcp_tools or chat_node
"""

from __future__ import annotations

import json
import logging
from functools import partial
from typing import Literal, List

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command
from routes.agent.nodes.helpers.agui_helpers import emit_state

from routes.agent.nodes.helpers.model import get_model
from routes.agent.state import AgentState, PlanTask
from utils.prompt_loader import render_prompt

logger = logging.getLogger(__name__)


def _user_question(messages: list) -> str:
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage) and msg.content.strip():
            return msg.content
    return ""


def _context_from_messages(messages: list) -> str:
    """Collect the last few AI response strings as context for planning."""
    parts = []
    for msg in messages:
        if isinstance(msg, AIMessage) and not getattr(msg, "tool_calls", None):
            content = getattr(msg, "content", "")
            if content and isinstance(content, str):
                parts.append(content[:800])
    return "\n\n---\n\n".join(parts[-4:])


async def plan_node(
    state: AgentState,
    config: RunnableConfig,
    mcp_tools: list = None,
) -> Command[Literal["mcp_tools", "__end__"]]:
    """
    HITL plan node.
    - If execution_plan already in state (set by a previous run before interrupt),
      skip regeneration and go straight to interrupt() for resume.
    - Otherwise: generate plan, emit to state, then interrupt().
    - If no plan / rejected: goto __end__ (chat_node initial answer was sufficient).
    """
    mcp_tools = mcp_tools or []

    # No MCP tools → skip to synthesis
    if not mcp_tools:
        return Command(goto="__end__", update={"execution_plan": []})

    existing_plan: List[PlanTask] = state.get("execution_plan") or []

    if not existing_plan:
        # ── First pass: generate the plan ─────────────────────────────
        question = _user_question(state.get("messages", []))
        if not question:
            return Command(goto="__end__", update={"execution_plan": []})

        context = _context_from_messages(state.get("messages", []))

        logs = list(state.get("logs", []))
        logs.append({"message": "Building execution plan…", "done": False})
        await emit_state(config, {**state, "logs": logs})

        tool_descriptions = []
        for t in mcp_tools:
            name = getattr(t, "name", str(t))
            desc = getattr(t, "description", "")
            tool_descriptions.append(f"- {name}: {desc[:120]}")
        tool_list = "\n".join(tool_descriptions)

        model = get_model(state)
        plan_prompt = render_prompt(
            "plan",
            tool_list=tool_list,
            question=question,
            context=context or "(none)",
        )
        plan_messages = [SystemMessage(content=plan_prompt)]

        plan_tasks: List[PlanTask] = []
        try:
            response = await model.ainvoke(plan_messages, config)
            raw = response.content.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                plan_tasks = [
                    PlanTask(
                        id=t.get("id", f"task_{i}"),
                        name=t.get("name", t.get("toolName", "?")),
                        toolName=t.get("toolName", ""),
                        status="pending",
                    )
                    for i, t in enumerate(parsed)
                    if t.get("toolName")
                ]
        except Exception as e:
            logger.warning("Plan generation failed: %s", e)
            plan_tasks = []

        await emit_state(config, {**state, "logs": logs, "execution_plan": plan_tasks, "pending_approval": True})

        return Command(
            goto="__end__",
            update={"execution_plan": plan_tasks, "logs": logs, "pending_approval": True},
        )

    last_msg = ""
    for msg in reversed(state.get("messages", [])):
        role = getattr(msg, "type", None) or (msg.get("role") if isinstance(msg, dict) else None)
        if role in ("human", "user"):
            last_msg = (msg.content if hasattr(msg, "content") else msg.get("content", "")).strip().lower()
            break

    if last_msg in ("rejected", "false", "no", "deny"):
        logger.info("User rejected execution plan")
        return Command(goto="__end__", update={"execution_plan": [], "logs": [], "pending_approval": False})

    running_plan = [
        PlanTask(id=t["id"], name=t["name"], toolName=t["toolName"], status="running")
        for t in existing_plan
    ]
    return Command(goto="mcp_tools", update={"execution_plan": running_plan, "logs": [], "pending_approval": False})


def make_plan_node(mcp_tools: list):
    """Factory: bind mcp_tools list into plan_node via partial."""
    return partial(plan_node, mcp_tools=mcp_tools)
