from abc import ABC, abstractmethod


class BaseTool(ABC):
    """Base class for all debate tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name used in Ollama tool calling schema."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Description shown to the LLM in the tool schema."""

    @property
    @abstractmethod
    def parameters(self) -> dict:
        """Ollama JSON schema for tool parameters."""

    @abstractmethod
    def execute(self, **kwargs) -> str:
        """Run the tool and return a string result."""
