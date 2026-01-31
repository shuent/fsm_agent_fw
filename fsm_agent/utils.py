import inspect
from typing import Any, Dict, List, Optional
from google.genai import types
from .fsm import FSM
from .tool_registry import ToolRegistry


def generate_orchestrator_guide(fsm: FSM, tool_registry: ToolRegistry) -> str:
    """
    Generates a guide for the orchestrator (LLM) describing the current state,
    valid transitions, and available tools.
    """
    guide = []

    # Current State & Transitions
    guide.append(f"Current State: {fsm.current_state}")
    next_states = fsm.get_next_states()
    if next_states:
        guide.append(f"Valid Next States: {', '.join(next_states)}")
    else:
        guide.append("Valid Next States: None (Terminal State)")

    # Available Tools (Just listing names for the guide, schema is passed separately)
    # guide.append("\nAvailable Tools:")
    # for tool in tool_registry.get_tools():
    #     guide.append(f"- {tool.__name__}: {tool.__doc__ or 'No description'}")

    return "\n".join(guide)


def tools_to_google_ai_schema(tool_registry: ToolRegistry) -> List[types.Tool]:
    """
    Converts registered tools to Google GenAI Tool format using function_to_tool mechanism.
    Since the google-genai SDK 0.x (assumed) might have helpers or we manually build.
    Actually, referencing modern google-genai usage, we can pass functions directly to `GenericTool` or similar
    if using higher level abstractions, but for raw `types.Tool`, we usually wrap declarations.

    However, the simplest way with the google-genai SDK is often just passing the functions list
    if the SDK supports automatic conversion, OR simpler: just return the list of functions
    and let the client handling loop manage the `tools` arg in `generate_content` / `messages`.

    BUT, the prompt asked for "tools_to_anthropic_schema"-like functional.
    The SDK `google.genai` usually wants a `tool_config` or list of `Tool`.

    Let's assume we return a simple list of callable functions for the new client to parse
    OR we construct `types.Tool` manually if needed.

    Wait, `google-genai` (the new SDK) `types.Tool` takes `function_declarations`.
    Let's try to simple thing: providing the python functions directly might work with some clients,
    but to be safe and explicit (like the framework implies), let's just return the tool definition.

    Actually, looking at `google-genai` Python SDK docs (implied knowledge):
    It supports passing a list of tools where a tool can be a function declaration.

    Let's implement a simple conversion helper.
    """

    # In the `google-genai` SDK, often we can pass functions directly to the `tools` argument of `generate_content`.
    # So this helper might just basically return the list of functions?
    # Or cleaner: return a generic `types.Tool` object containing declarations?

    # Let's just return the list of functions. The SDK is smart enough to introspect them.
    # Ref: `client.models.generate_content(..., tools=[func1, func2])`

    return tool_registry.get_tools()
