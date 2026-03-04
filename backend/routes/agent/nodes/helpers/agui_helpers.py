"""
AG-UI state emit helper.

WHY THIS EXISTS:
  copilotkit_emit_state() dispatches a custom LangGraph event named
  "copilotkit_manually_emit_intermediate_state", but the backend's AG-UI
  runtime (ag_ui_langgraph) only handles events named "manually_emit_state"
  (see ag_ui_langgraph.types.CustomEventNames.ManuallyEmitState).

  Calling this function instead ensures the StateSnapshotEvent is correctly
  forwarded to the frontend via the AG-UI → CopilotKit Runtime bridge.

SERIALIZATION NOTE:
  state may contain LangChain Message objects (state["messages"]) which are
  NOT JSON-serializable by adispatch_custom_event. We strip them out and only
  send the lightweight UI-facing fields. This avoids silent failures where
  the event is dropped because of a serialization error.
"""

import asyncio
import logging
from typing import Any

from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.runnables import RunnableConfig

logger = logging.getLogger(__name__)

_AGUI_EMIT_STATE_EVENT = "manually_emit_state"
_SKIP_KEYS = {"messages", "uploaded_docs"}


async def emit_state(config: RunnableConfig, state: Any) -> bool:
    """
    Emit intermediate state to the frontend via AG-UI protocol.

    Dispatches the 'manually_emit_state' custom event which ag_ui_langgraph
    converts into a StateSnapshotEvent, forwarded to the frontend by
    CopilotKit Runtime's LangGraphHttpAgent.

    Parameters
    ----------
    config : RunnableConfig
        The LangGraph node config passed into the node function.
    state : Any
        The state snapshot to emit. LangChain Message objects in
        state["messages"] are automatically excluded.
    """
    if isinstance(state, dict):
        serializable = {k: v for k, v in state.items() if k not in _SKIP_KEYS}
    else:
        serializable = state

    try:
        await adispatch_custom_event(
            _AGUI_EMIT_STATE_EVENT,
            serializable,
            config=config,
        )
        await asyncio.sleep(0.02)
    except Exception as e:
        logger.warning("emit_state failed: %s", e)
        return False
    return True
