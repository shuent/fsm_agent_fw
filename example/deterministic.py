import os
import sys

# Add parent directory to path to import fsm_agent
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
from google import genai
from fsm_agent import FSM, ToolRegistry

import time

# Load environment variables
load_dotenv()


def main():
    print("Initializing Deterministic FSM Agent (Elegant Dispatch)...")

    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

    # Shared context for tools and orchestrator
    context = {}

    # 1. Define Tools
    tools = ToolRegistry()

    @tools.register
    def report_sentiment(score: int, reason: str) -> str:
        """Report the sentiment score of the text."""
        print(f"  -> [Tool] Reporting sentiment: Score={score}, Reason={reason}")
        context["sentiment_score"] = score
        context["sentiment_reason"] = reason
        return "Score recorded."

    # 2. Define FSM
    fsm = FSM(
        states={
            "start": ["analyzing"],
            "analyzing": ["approved", "rejected"],
            "approved": ["end"],
            "rejected": ["end"],
            "end": [],
        },
        initial_state="start",
        terminal_states=["end"],
    )

    # 3. Input Data
    user_input = (
        "This framework is absolutely amazing and perfect for my needs! I love it."
    )

    print(f'Input Text: "{user_input}"')

    # 4. State Handlers (The "Deterministic Brain")
    # Associated with the Map (FSM), these functions handle the logic for each node.

    def on_analyzing():
        # Action: Mocked sentiment extraction (Simulating Work)
        print("Action: Mocking sentiment analysis (No LLM call)...")
        score = 95 if "amazing" in user_input.lower() else 50

        # This updates the context
        tools.execute("report_sentiment", score=score, reason="Keyword analysis")

        # After work is done, IMMEDIATELY decide the next state and transition.
        # This prevents re-looping into the same state.
        next_state = "approved" if score >= 80 else "rejected"
        fsm.transition(next_state)

    def on_finished():
        print(f"Action: Finalizing {fsm.current_state} state...")
        fsm.transition("end")

    # Orchestration logic mapped directly to FSM states
    state_handlers = {
        "start": lambda: fsm.transition("analyzing"),
        "analyzing": on_analyzing,
        "approved": on_finished,
        "rejected": on_finished,
    }

    # 5. Execution Loop (The "Engine")
    # This loop is generic; it doesn't know about specific business logic.
    while not fsm.is_terminal():
        current_state = fsm.current_state
        print(f"\n[FSM] Current State: {current_state}")

        handler = state_handlers.get(current_state)
        if handler:
            handler()
        else:
            raise RuntimeError(f"No handler for state: {current_state}")

    print("\nWorkflow completed.")


if __name__ == "__main__":
    main()
