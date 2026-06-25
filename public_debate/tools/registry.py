from public_debate.tools import (
    BaseTool,
    SearchTool,
    FallacyDetectorTool,
    QuoteTool,
    PollTool,
    SentimentTool,
    JokeTool,
)
import random


class ToolRegistry:
    """Registry of available debate tools. Handles assignment and schema generation."""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        for tool_cls in [SearchTool, FallacyDetectorTool, QuoteTool, PollTool, SentimentTool, JokeTool]:
            instance = tool_cls()
            self._tools[instance.name] = instance

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool:
        return self._tools[name]

    def get_all(self) -> list[BaseTool]:
        return list(self._tools.values())

    def get_schemas(self, tools: list[BaseTool]) -> list[dict]:
        """Return Ollama-format tool schemas for a subset of tools."""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in tools
        ]

    def assign_random(self) -> tuple[list[BaseTool], list[BaseTool]]:
        """Randomly split all tools into two groups for Speaker A and B."""
        all_tools = self.get_all()
        shuffled = random.sample(all_tools, len(all_tools))
        mid = len(shuffled) // 2
        return shuffled[:mid], shuffled[mid:]

    def judge_tools(self) -> list[BaseTool]:
        """Return the tools available to the judge (search only)."""
        return [self._tools["search"]]
