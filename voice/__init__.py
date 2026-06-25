"""Voice module — TTS generation and audio playback."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from voice.player import cleanup_audio, play_audio, play_audio_files
from voice.provider import TTSProvider, get_provider

logger = logging.getLogger(__name__)

_ROLE_ICONS: dict[str, str] = {
    "moderator": "🎙️",
    "proposer": "🛡️",
    "critic": "⚔️",
    "speaker_a": "🛡️",
    "speaker_b": "⚔️",
    "judge": "⚖️",
}

_provider: TTSProvider | None = None


def _get_provider() -> TTSProvider:
    global _provider
    if _provider is None:
        _provider = get_provider()
    return _provider


def speak(text: str, role: str) -> None:
    """Generate speech from text and play it aloud.

    Args:
        text: The text to synthesize.
        role: Role key ('moderator', 'proposer', 'critic',
              'speaker_a', 'speaker_b', 'judge').
    """
    try:
        provider = _get_provider()
        voice = provider.get_voice(role)
        icon = _ROLE_ICONS.get(role, "🔊")
        label = role.replace("_", " ").title()
        logger.info("speak(): role='%s', voice='%s', text_len=%d", role, voice, len(text))

        from tui_formatter.console import console
        with console.status(f"  {icon} {label} — Generating speech...", spinner="dots"):
            audio_paths = asyncio.run(provider.generate_audio(text, voice))
        play_audio_files(audio_paths)
        for audio_path in audio_paths:
            cleanup_audio(audio_path)
    except Exception as e:
        logger.warning("Voice speak failed: %s. Continuing without audio.", e)


def generate_audio(text: str, role: str) -> list[Path]:
    """Generate audio from text without playing it.

    Args:
        text: The text to synthesize.
        role: Role key.

    Returns:
        List of Paths to generated audio files, in playback order.
    """
    provider = _get_provider()
    voice = provider.get_voice(role)
    return asyncio.run(provider.generate_audio(text, voice))


def get_voice_assignment() -> dict[str, str]:
    """Return the full role-to-voice mapping for the active provider."""
    return _get_provider().voice_assignment()


__all__ = [
    "speak",
    "generate_audio",
    "get_voice_assignment",
    "play_audio",
    "cleanup_audio",
    "TTSProvider",
    "get_provider",
]