"""Shared Rich Console and Theme for the agent-harness CLI."""

import sys

from rich.console import Console
from rich.theme import Theme

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DEBATE_THEME = Theme(
    {
        "proposer": "bold cyan",
        "proposer.text": "cyan",
        "critic": "bold magenta",
        "critic.text": "magenta",
        "speaker_a": "bold cyan",
        "speaker_a.text": "cyan",
        "speaker_b": "bold magenta",
        "speaker_b.text": "magenta",
        "judge": "bold gold1",
        "judge.text": "gold1",
        "system": "dim",
        "claim": "bold white",
        "tool_result": "bold yellow",
        "tool_result.title": "yellow",
        "tool_result.text": "yellow",
    }
)

console = Console(theme=DEBATE_THEME)
