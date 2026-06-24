"""agent-harness: Multi-mode AI debate agents with rich CLI output."""

from tui_formatter.console import console
from tui_formatter.formatter import (
    print_claim,
    print_motion,
    print_speaker_label,
    print_speaker_response,
    prompt_claim,
    prompt_input,
    prompt_motion,
    print_thinking,
    print_verdict,
    stream_text,
    print_moderator,
)
from tui_formatter.roles import (
    CRITIC,
    JUDGE,
    MODERATOR,
    PROPOSER,
    SPEAKER_A,
    SPEAKER_B,
    ROLES,
    Role,
)

__all__ = [
    "console",
    "print_claim",
    "print_motion",
    "print_speaker_label",
    "print_speaker_response",
    "prompt_claim",
    "prompt_input",
    "prompt_motion",
    "print_thinking",
    "print_verdict",
    "stream_text",
    "print_moderator",
    "CRITIC",
    "JUDGE",
    "MODERATOR",
    "PROPOSER",
    "SPEAKER_A",
    "SPEAKER_B",
    "ROLES",
    "Role",
]