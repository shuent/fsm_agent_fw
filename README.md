# FSM Agent Framework

[日本語ver](README.ja.md)

**An Ultra-Lightweight AI Agent Framework Based on FSM (Finite State Machines)**

By eliminating complex abstractions like LangGraph and maximizing the inference capabilities and structured outputs of LLMs, this framework achieves both "minimal code" and a "clear thought process."

---

## What the Framework Provides

This framework provides only **two core components**:

### 1. `FSM` Class
A simple class for defining and validating state transitions.

```python
from fsm_agent import FSM

fsm = FSM(
    states={
        "start": ["researching"],
        "researching": ["writing"],
        "writing": ["reviewing"],
        "reviewing": ["writing", "end"],
        "end": []
    },
    initial_state="start",
    terminal_states=["end"]
)

# Usage examples
fsm.get_next_states()  # Get list of possible next states from current state
fsm.transition("researching")  # Transition state (with validation)
fsm.is_terminal()  # Check if current state is a terminal state
```

**Features:**
- Definition and validation of state transitions
- Management of the current state
- Retrieval of accessible states
- Terminal state determination

### 2. `ToolRegistry` Class
A class to register and manage Python functions as tools.

```python
from fsm_agent import ToolRegistry

tools = ToolRegistry()

@tools.register
def research_web(topic: str) -> str:
    """Conduct web research on the specified topic"""
    return f"Research completed: {topic}"

@tools.register
def write_article(content: str) -> str:
    """Write an article"""
    return f"Article: {content}"

# Usage examples
tools.execute("research_web", topic="AI")
tools.get_tool_schemas()  # Get tool schemas formatted for LLMs
```

**Features:**
- Tool registration via decorators
- Tool execution
- Automatic schema generation for LLMs (OpenAI/Anthropic formats)
- Retrieval of registered tool lists

### 3. Helper Functions

```python
# Generate tool schemas in Google GenAI format
tools_to_google_ai_schema(tool_registry)

# Generate guide text for the orchestrator
generate_orchestrator_guide(fsm, tool_registry)
```

---

## Design Philosophy for Agents

When building an agent with this framework, keep these three roles in mind:

### 3 Roles

#### ① FSM (The Map)
Plain dictionary data defining "from which state, to which state" transitions are allowed.

- **Role**: Guardrails to prevent the agent from deviating.
- **Design Policy**: One-way for workflows; branching and loops for autonomous tasks.
- **Presentation to AI**: The prompt always displays "Current State" and "Available Transition Options."

#### ② Tools (The Toolbox)
A group of tools registered as Python functions.

- **Role**: Interaction with the real world (APIs, DBs, Calculations).
- **Design Policy**: Do not distinguish between "Specialized Agents" and "Simple Tools"—define everything as Python functions.
- **Unified Interface**: Sub-agent calls and single tool executions are abstracted as the same "function execution."

#### ③ Orchestrator (The Brain)
The LLM that manages conversation history and makes decisions based on the FSM.

- **Role**: Operating the FSM, selecting tools, and maintaining context.
- **Thought Process**:
  1. Read conversation history (Context).
  2. Compare current state with "Next Options" based on the FSM.
  3. Declare "What to do next" via structured output.
- **Implementation**: Implemented freely by the user (The framework does not enforce logic here).

---

## Basic Usage

### Step 1: Define FSM and Tools

```python
import os
from google import genai
from fsm_agent import FSM, ToolRegistry, generate_orchestrator_guide, tools_to_google_ai_schema

# Tool Definition
tools = ToolRegistry()

@tools.register
def research_web(topic: str) -> str:
    """Conduct web research on the specified topic"""
    return f"Research completed: {topic} is important because..."

@tools.register
def write_article(research_result: str) -> str:
    """Write an article based on research results"""
    return f"Article: Based on research, here's the article..."

@tools.register
def review_article(article: str) -> str:
    """Review the article"""
    if len(article) > 50:
        return "APPROVED"
    else:
        return "REJECTED: Too short"

# FSM Definition
fsm = FSM(
    states={
        "start": ["researching"],
        "researching": ["writing"],
        "writing": ["reviewing"],
        "reviewing": ["writing", "end"],  # Return to writing if rejected
        "end": []
    },
    initial_state="start",
    terminal_states=["end"]
)
```

### Step 2: Implement Orchestrator

```python
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# Special Tool: State Transition
@tools.register
def transition_state(next_state: str, reason: str = "") -> str:
    """Transition to the next state"""
    fsm.transition(next_state)
    return f"Transitioned to: {next_state}"
```

### Step 3: Main Loop

```python
from google.genai import types

# Initialize Chat History
chat_history = []
user_request = "Create an article about the latest trends in AI"
chat_history.append(types.Content(role="user", parts=[types.Part(text=user_request)]))

# Message-Driven Autonomous Loop
while not fsm.is_terminal():
    # Generate Dynamic System Prompt
    orchestrator_guide = generate_orchestrator_guide(fsm, tools)
    system_instruction = f"""
    You are the leader of a content production team.
    {orchestrator_guide}
    """

    # Call LLM
    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=chat_history,
        config=types.GenerateContentConfig(
            tools=tools_to_google_ai_schema(tools),
            system_instruction=system_instruction
        )
    )
    
    # Add to History
    chat_history.append(response.candidates[0].content)
    
    # Execute Tool and Process Result
    part = response.candidates[0].content.parts[0]
    if part.function_call:
        result = tools.execute(part.function_call.name, **part.function_call.args)
        
        # Add Result to History
        chat_history.append(types.Content(
            role="user",
            parts=[types.Part.from_function_response(
                name=part.function_call.name,
                response={"result": result}
            )]
        ))

print("Workflow completed!")
```

---

## Architecture: Message-Driven Autonomous Loop

The cycle below rotates between the Orchestrator (LLM) and the Execution Environment (Python):

```
┌─────────────────────────────────────────┐
│ 1. Injection (Context Injection)        │
│    - Conversation History               │
│    - Current State                      │
│    - Accessible Next States             │
│    - Available Tools                    │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│ 2. Declaration (AI Declaration)         │
│    - LLM structured output for next action
│    - call_tool or transition            │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│ 3. Execution (Execution)                │
│    - Python runs tool or state transition
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│ 4. Accumulation (Memory Accumulation)   │
│    - Append execution results to messages
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│ 5. Termination Check                    │
│    - Check if terminal state is reached │
└─────────────────────────────────────────┘
```

---

## State Management & Shared Context

This framework **does not provide library-level context sharing features**.

### Why?
1.  **Maintaining Simplicity**: Complex dependency injection mechanisms reduce code readability and make debugging difficult.
2.  **User-Space Control**: Whether state is held in class instance variables, global variables, or a database should depend on the application requirements.
3.  **Token Efficiency**: To encourage patterns where massive data is not passed to the orchestrator, but handled behind the scenes between tools (Shared Context).

### Recommended Pattern: "Hidden Context"
Huge data (article bodies, full search results) clogs the orchestrator's context window. We recommend a design where data is shared between tools, and only a "summary" is returned to the orchestrator.

```python
# Shared Context (Defined in user code)
context = {}

@tools.register
def heavy_task() -> str:
    # Generate massive data
    data = generate_huge_data() 
    # Store in context
    context["data_id"] = data 
    # Return only summary to orchestrator
    return "Data generated and stored in context."

@tools.register
def next_task() -> str:
    # Read from context (Not via Orchestrator)
    data = context.get("data_id") 
    process(data)
    return "Processed data from context."
```

By doing this, the orchestrator controls only the "flow of data" without seeing the actual "content of data," minimizing token consumption.

---

## Design Philosophy

### Why this "Thinness"?

#### 1. **"Give the Map, and the LLM Can Walk"**
Modern LLMs can move autonomously without complex external control logic if given logical constraints like an FSM via prompts.

#### 2. **Flattening Tools and Agents**
We erase the boundary of "from here is the agent's job, from here is the tool's job." By defining everything as Python functions, the design becomes extremely simple.

#### 3. **Total Trust in Structured Output**
The era of fearing parse errors is over. By directly using the structured output features of OpenAI or Anthropic, we connect the LLM's "Declaration" directly to code logic.

#### 4. **User Implements Orchestration**
The framework provides only the minimal primitives (FSM, ToolRegistry). How to write the loop, error handling, logging, etc., can be freely implemented according to user requirements.

---

## Differences from LangGraph

| Item | FSM Agent | LangGraph |
|------|-----------|-----------|
| **Abstraction Level** | Minimal (FSM + ToolRegistry) | High (Graph, Node, Edge) |
| **Loop Control** | User Implements | Framework Provided |
| **State Management** | Simple FSM | StateGraph with reducers |
| **Learning Cost** | Low (Basic Python only) | Medium-High (Many unique concepts) |
| **Customizability** | Completely Free | Within Framework Limits |
| **Scope** | Simple workflows to mid-scale tasks | Large-scale, complex multi-agents |

---

## License

MIT

---

## Summary

This framework maximizes LLM inference capabilities by providing **minimal primitives**.

- **Framework Provides**: `FSM` and `ToolRegistry`
- **User Implements**: Orchestration loop, prompt design, error handling
- **LLM Handles**: State transition decisions, tool selection, task execution

It is a new agent framework that balances simplicity and flexibility.