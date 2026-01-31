import inspect
from typing import Any, Callable, Dict, List


class ToolRegistry:
    """
    Registry for managing python functions as tools for the agent.
    """

    def __init__(self):
        self._tools: Dict[str, Callable] = {}

    def register(self, func: Callable):
        """
        Decorator to register a function as a tool.
        """
        self._tools[func.__name__] = func
        return func

    def execute(self, name: str, **kwargs) -> Any:
        """
        Executes a registered tool by name.
        """
        if name not in self._tools:
            raise ValueError(f"Tool '{name}' not found.")
        return self._tools[name](**kwargs)

    def get_tools(self) -> List[Callable]:
        """Returns a list of all registered tool functions."""
        return list(self._tools.values())
