import re


def enforce_limit(text: str, max_chars: int = 300) -> str:
    if len(text) <= max_chars:
        return text

    truncated = text[:max_chars]
    sentences = re.split(r"(?<=[.!?])\s+", truncated)
    return " ".join(sentences[:-1]) + " …"


def format_opponent_argument(speaker_label: str, content: str) -> list[dict]:
    """Wrap the opponent's last argument as a user message."""
    return [{"role": "user", "content": f"{speaker_label}'s argument: {content}"}]


def format_tool_result(tool_name: str, result: str) -> dict:
    """Format a tool result as a message for the LLM context."""
    return {
        "role": "tool",
        "name": tool_name,
        "content": result,
    }
