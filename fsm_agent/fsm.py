from typing import Dict, List, Optional


class FSM:
    """
    Finite State Machine for managing agent states.
    """

    def __init__(
        self,
        states: Dict[str, List[str]],
        initial_state: str,
        terminal_states: List[str],
    ):
        """
        Initialize the FSM.

        Args:
            states: A dictionary where key is the state name and value is a list of allowed next states.
            initial_state: The starting state.
            terminal_states: A list of states where the workflow ends.
        """
        self.states = states
        self.current_state = initial_state
        self.terminal_states = terminal_states

        # Validation
        if initial_state not in states:
            raise ValueError(
                f"Initial state '{initial_state}' is not defined in states."
            )
        for state, transitions in states.items():
            for next_state in transitions:
                if next_state not in states:
                    raise ValueError(
                        f"Transition target '{next_state}' from '{state}' is not defined in states."
                    )

    def get_next_states(self) -> List[str]:
        """Returns a list of allowable next states from the current state."""
        return self.states.get(self.current_state, [])

    def transition(self, next_state: str):
        """
        Transitions to the next state if allowed.

        Raises:
            ValueError: If the transition is invalid.
        """
        if next_state not in self.get_next_states():
            raise ValueError(
                f"Invalid transition: Cannot move from '{self.current_state}' to '{next_state}'. "
                f"Allowed transitions: {self.get_next_states()}"
            )
        self.current_state = next_state

    def is_terminal(self) -> bool:
        """Returns True if the current state is a terminal state."""
        return self.current_state in self.terminal_states
