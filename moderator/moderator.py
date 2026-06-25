"""Moderator agent — TV debate host that introduces, transitions, and closes."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from moderator.moderator_prompt import (
    MODERATOR_CLOSING_PROMPT,
    MODERATOR_OPENING_PROMPT,
    MODERATOR_TRANSITION_PROMPT,
)

from tui_formatter.roles import SPEAKER_A, SPEAKER_B

if TYPE_CHECKING:
    from ollama import Client

logger = logging.getLogger(__name__)

MAX_MODERATOR_CHARS = 300


def _format_transcript(transcript: list[tuple[str, str]]) -> str:
    """Format transcript entries into a readable block for the moderator."""
    return "\n".join(f"{speaker}: {content}" for speaker, content in transcript)


def opening(client: Client, model: str, motion: str, format_type: str = "public") -> str:
    """Generate the moderator's opening introduction.

    Args:
        client: Ollama client instance.
        model: Model name to use.
        motion: The debate motion or claim.
        format_type: "public" or "proposer_critic" — affects role labels.

    Returns:
        The moderator's opening text.
    """
    if format_type == "proposer_critic":
        role_context = (
            f"The Proposer will argue for the claim, and the Critic will argue against it. "
            f"Claim: {motion}. "
            f"The Proposer speaks first. End by giving the Proposer the floor."
        )
    else:
        role_context = (
            f"{SPEAKER_A.label} will argue for the motion, and {SPEAKER_B.label} will argue against it. "
            f"Motion: {motion}. "
            f"{SPEAKER_A.label} speaks first. End by giving {SPEAKER_A.label} the floor."
        )

    messages = [{"role": "user", "content": role_context}]

    try:
        response = client.chat(
            model=model,
            messages=[{"role": "system", "content": MODERATOR_OPENING_PROMPT}] + messages,
        )
        text = response.message.content if response.message else ""
    except Exception as e:
        logger.warning("Moderator opening failed: %s. Skipping moderator segment.", e)
        return ""

    if len(text) > MAX_MODERATOR_CHARS:
        text = text[:MAX_MODERATOR_CHARS].rsplit(".", 1)[0] + "."

    return text.strip()


def transition(
    client: Client,
    model: str,
    transcript_so_far: list[tuple[str, str]],
    next_speaker: str,
    round_num: int,
    total_rounds: int,
) -> str:
    """Generate a transition between speakers.

    Args:
        client: Ollama client instance.
        model: Model name to use.
        transcript_so_far: List of (speaker_name, content) tuples.
        next_speaker: Label of the upcoming speaker (e.g., "Speaker B").
        round_num: Current round number (1-indexed).
        total_rounds: Total number of rounds.

    Returns:
        The moderator's transition text.
    """
    transcript_text = _format_transcript(transcript_so_far)
    prompt = (
        f"Round {round_num} of {total_rounds}. "
        f"Here is what has been said so far:\n{transcript_text}\n\n"
        f"Now hand the floor to {next_speaker} by name. "
        f"End your response by giving {next_speaker} the mic."
    )

    messages = [{"role": "user", "content": prompt}]

    try:
        response = client.chat(
            model=model,
            messages=[{"role": "system", "content": MODERATOR_TRANSITION_PROMPT}] + messages,
        )
        text = response.message.content if response.message else ""
    except Exception as e:
        logger.warning("Moderator transition failed: %s. Skipping moderator segment.", e)
        return ""

    if len(text) > MAX_MODERATOR_CHARS:
        text = text[:MAX_MODERATOR_CHARS].rsplit(".", 1)[0] + "."

    return text.strip()


def closing(
    client: Client,
    model: str,
    transcript: list[tuple[str, str]],
    format_type: str = "public",
) -> str:
    """Generate the moderator's closing before the judge.

    Args:
        client: Ollama client instance.
        model: Model name to use.
        transcript: Full debate transcript as (speaker_name, content) tuples.
        format_type: "public" or "proposer_critic".

    Returns:
        The moderator's closing text.
    """
    transcript_text = _format_transcript(transcript)
    prompt = f"The debate is over. Here is the full transcript:\n{transcript_text}\n\nWrap it up and hand off to the judge."

    messages = [{"role": "user", "content": prompt}]

    try:
        response = client.chat(
            model=model,
            messages=[{"role": "system", "content": MODERATOR_CLOSING_PROMPT}] + messages,
        )
        text = response.message.content if response.message else ""
    except Exception as e:
        logger.warning("Moderator closing failed: %s. Skipping moderator segment.", e)
        return ""

    if len(text) > MAX_MODERATOR_CHARS:
        text = text[:MAX_MODERATOR_CHARS].rsplit(".", 1)[0] + "."

    return text.strip()