import os
import sys
from dotenv import load_dotenv
from google import genai
from google.genai import types

from fsm_agent import (
    FSM,
    ToolRegistry,
    generate_orchestrator_guide,
    tools_to_google_ai_schema,
)

# Load environment variables
load_dotenv()


def main():
    print("Initializing FSM Agent with Google GenAI...")

    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

    # 1. Define Tools
    tools = ToolRegistry()

    @tools.register
    def research_web(topic: str) -> str:
        """Researches a topic on the web."""
        print(f"\n[Tool] Researching: {topic}")
        return f"Research results for {topic}: It is a vast field with many interesting aspects."

    @tools.register
    def write_article(topic: str, research_summary: str) -> str:
        """Writes a short article based on research."""
        print(f"\n[Tool] Writing article on {topic}...")
        return f"Title: {topic}\n\nSummary: {research_summary}\n\n(Article content...)"

    @tools.register
    def review_article(article_content: str) -> str:
        """Reviews the article. Returns 'APPROVED' or 'REJECTED'."""
        print(f"\n[Tool] Reviewing article...")
        if len(article_content) > 10:  # Simple validation
            return "APPROVED"
        return "REJECTED: Too short."

    # 2. Define FSM
    fsm = FSM(
        states={
            "start": ["researching"],
            "researching": ["writing"],
            "writing": ["reviewing"],
            "reviewing": ["writing", "end"],
            "end": [],
        },
        initial_state="start",
        terminal_states=["end"],
    )

    # Special tool for state transition
    @tools.register
    def transition_state(next_state: str, reason: str = "") -> str:
        """Transitions the agent to the next state."""
        print(f"\n[FSM] Transitioning to: {next_state} (Reason: {reason})")
        try:
            fsm.transition(next_state)
            return f"Successfully transitioned to {next_state}"
        except ValueError as e:
            return f"Error transitioning: {e}"

    # 3. Execution Loop

    # We maintain the chat history manually to follow the "Message Driven" pattern
    # and to inject the dynamic system prompt (current state).

    chat_history = []

    # Initial user intent
    user_request = "Write a short article about Artificial Intelligence."
    chat_history.append(
        types.Content(role="user", parts=[types.Part(text=user_request)])
    )

    print(f"User Request: {user_request}")

    step_count = 0
    max_steps = 15

    while not fsm.is_terminal() and step_count < max_steps:
        step_count += 1
        print(f"\n--- Step {step_count} (State: {fsm.current_state}) ---")

        # Dynamic System Prompt
        orchestrator_guide = generate_orchestrator_guide(fsm, tools)
        system_instruction = f"""
        You are an autonomous agent managed by a Finite State Machine.
        
        {orchestrator_guide}
        
        Your Goal: {user_request}
        
        Instructions:
        1. Check your current state.
        2. Use tools allowed for the task phases (research -> write -> review).
        3. VERY IMPORTANT: You MUST use the `transition_state` tool to move to the next state when you are done with the current state's work.
        4. When the work is approved in the 'reviewing' state, transition to 'end'.
        """

        # Call generic generic generate_content with tools
        # We pass the list of tool functions; the SDK handles schema generation.
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=chat_history,
            config=types.GenerateContentConfig(
                tools=tools_to_google_ai_schema(tools),
                system_instruction=system_instruction,
                temperature=0.0,  # Deterministic
            ),
        )

        # Append model response to history
        chat_history.append(response.candidates[0].content)

        # Check for function calls
        if response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.function_call:
                    fn_name = part.function_call.name
                    fn_args = part.function_call.args

                    # Execute tool
                    try:
                        result = tools.execute(fn_name, **fn_args)
                        print(f"  -> Tool Output: {str(result)[:100]}...")
                    except Exception as e:
                        result = f"Error executing {fn_name}: {e}"
                        print(f"  -> Tool Error: {result}")

                    # Append function response to history
                    # Google GenAI requires FunctionResponse parts
                    chat_history.append(
                        types.Content(
                            role="user",
                            parts=[
                                types.Part.from_function_response(
                                    name=fn_name, response={"result": result}
                                )
                            ],
                        )
                    )
                elif part.text:
                    print(f"Thought: {part.text}")

    if fsm.is_terminal():
        print("\nWorkflow completed successfully!")
    else:
        print("\nWorkflow stopped (max steps reached or other reason).")


if __name__ == "__main__":
    main()
