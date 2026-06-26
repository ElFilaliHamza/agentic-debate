"""Display formatting functions for debate CLI output."""

from __future__ import annotations

import os
import time

from rich.panel import Panel
from tui_formatter.console import console
from tui_formatter.roles import Role, TOOL_ICONS

TYPING_DELAY = float(os.getenv("TYPING_DELAY", "0.02"))


def print_claim(claim: str) -> None:
    """Display the opening claim in a panel."""
    console.print()
    console.print(
        Panel(
            claim,
            title="📋 Claim to debate",
            border_style="white",
            padding=(1, 2),
        )
    )
    console.print()


def print_motion(motion: str) -> None:
    """Display the opening motion in a panel."""
    console.print()
    console.print(
        Panel(
            motion,
            title="📋 Motion",
            border_style="white",
            padding=(1, 2),
        )
    )
    console.print()


def prompt_input(label: str, title: str = "🤖 Agentic Debate ") -> str:
    """Display a styled prompt panel and return user input."""
    console.print()
    console.print(
        Panel(
            f"[bold]{label}[/bold]",
            title=title,
            border_style="cyan",
            padding=(1, 2),
        )
    )
    return input("> ").strip()


def prompt_claim() -> str:
    """Prompt for a claim, display it as a claim panel, and return it."""
    claim = prompt_input("Enter a factual claim to debate")
    print_claim(claim)
    return claim


def prompt_motion() -> str:
    """Prompt for a motion, display it as a motion panel, and return it."""
    motion = prompt_input("Enter the debate motion")
    print_motion(motion)
    return motion


def print_thinking(role: Role) -> None:
    """Display a dim 'thinking' indicator before an API call."""
    console.print(f"  ⏳ {role.icon} {role.label} is thinking...", style="system")


def print_speaker_response(role: Role, text: str) -> None:
    """Display a speaker's argument with role-colored label and text."""
    console.print()
    console.print(f"{role.icon} {role.label}:", style=role.style)
    console.print(f"  {text}", style=role.text_style)
    console.print()


def print_speaker_label(role: Role) -> None:
    """Print just the speaker label (before streaming begins)."""
    console.print()
    console.print(f"{role.icon} {role.label}:", style=role.style, end="")


def stream_text(text: str, delay: float = TYPING_DELAY) -> None:
    """Stream text character-by-character via the Rich console."""
    for char in text:
        console.print(char, end="", highlight=False)
        time.sleep(delay)
    console.print()


def print_verdict(role: Role, text: str) -> None:
    """Display the judge's verdict in a gold-bordered panel."""
    console.print()
    console.print(
        Panel(
            text,
            title=f"{role.icon} Verdict",
            border_style="gold1",
            padding=(1, 2),
        )
    )
    console.print()


def print_tool_result(tool_name: str, result: str) -> None:
    """Display a tool result as a distinct inline block."""
    icon = TOOL_ICONS.get(tool_name, "🔧")
    label = tool_name.replace("_", " ").title()
    console.print()
    console.print(f"  {icon} {label}:", style="tool_result")
    console.print(f"    {result}", style="tool_result.text")
    console.print()


def print_tool_assignment(role, tools: list) -> None:
    """Display which tools a speaker has been assigned."""
    tool_names = [f"{TOOL_ICONS.get(t.name, '🔧')} {t.name}" for t in tools]
    console.print(
        f"  {role.icon} {role.label} tools: {', '.join(tool_names)}",
        style="system",
    )


def print_host(text: str) -> None:
    """Display the host's commentary with the host role style."""
    console.print()
    console.print("🎙️ Host:", style="host")
    console.print(f"  {text}", style="host.text")
    console.print()
